from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Literal
from uuid import uuid4

from sqlalchemy import select, update

from framework.starter_database.public import (
    SessionProvider,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    MessageResultUnknown,
)
from module_system.dal.dataobject.mail.mail_log_do import MailLogDO
from module_system.dal.dataobject.sms.sms_log_do import SmsLogDO
from module_system.definitions.enums.mail.mail_send_status_enum import MailSendStatusEnum
from module_system.definitions.enums.notification.delivery_attempt_stage_enum import (
    DeliveryAttemptStageEnum,
)
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum
from module_system.framework.notification.config.notification_delivery_settings import (
    NotificationDeliverySettings,
)
from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryAttempt,
    DeliveryRequestStartedCallback,
)
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.service.notification.notification_delivery_service import (
    NotificationDeliveryService,
)

_CHANNELS = {
    "mail": (MailLogDO, MailSendStatusEnum, "send_exception"),
    "sms": (SmsLogDO, SmsSendStatusEnum, "api_send_msg"),
}


@service(interface=NotificationDeliveryService)
class NotificationDeliveryServiceImpl(NotificationDeliveryService):
    database: SessionProvider = Inject()
    settings: NotificationDeliverySettings = Inject()

    async def execute[Result](
        self,
        kind: Literal["mail", "sms"],
        identifier: int,
        *,
        send: Callable[[DeliveryRequestStartedCallback], Awaitable[Result]],
        result_values: Callable[[Result], dict[str, int | str | None]],
    ) -> None:
        """集中执行投递状态转换；取消任务保留已有认领或未知状态供恢复核对。"""
        _, status, error_field = _CHANNELS[kind]
        attempt = await self._claim(kind, identifier)
        if attempt is None:
            return
        try:
            result = await send(partial(self._started, kind, identifier, attempt))
        except DeliveryCancelled:
            await self._finish(kind, identifier, attempt, send_status=status.CANCELLED.code)
            return
        except DeliveryDefiniteFailure as error:
            await self._finish(
                kind,
                identifier,
                attempt,
                send_status=status.FAILURE.code,
                **{error_field: type(error).__name__},
            )
            raise
        except Exception as error:
            await self._finish(
                kind,
                identifier,
                attempt,
                send_status=status.SENDING.code,
                **{error_field: type(error).__name__},
            )
            raise MessageResultUnknown("外发结果未知，需要核实厂商结果后处理") from error
        await self._finish(kind, identifier, attempt, **result_values(result))

    async def _claim(self, kind: str, identifier: int) -> DeliveryAttempt | None:
        """原子认领可重试记录，拒绝在途或结果未知的重复投递。"""
        model, status, _ = _CHANNELS[kind]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with self.database.transaction(propagation="requires_new") as session:
            entry = (
                await session.execute(select(model).where(model.id == identifier).with_for_update())
            ).scalar_one()
            if entry.send_status in {
                status.SUCCESS.code,
                status.IGNORE.code,
                status.CANCELLED.code,
            }:
                return None
            if entry.send_status == status.SENDING.code:
                raise MessageResultUnknown("外发结果未知，需要核实厂商结果后处理")
            if entry.send_claim_until is not None and entry.send_claim_until > now:
                raise DeliveryDefiniteFailure("当前投递已被领取")
            token = uuid4().hex
            await session.execute(
                update(model)
                .where(model.id == identifier)
                .values(
                    send_claim_token=token,
                    send_claim_until=now
                    + timedelta(seconds=self.settings.delivery_claim_lease_seconds),
                )
            )
        return DeliveryAttempt(claim_token=token)

    async def _started(self, kind: str, identifier: int, attempt: DeliveryAttempt) -> None:
        """以认领令牌标记网络请求已开始，失效认领不得继续外发。"""
        model, status, _ = _CHANNELS[kind]
        async with self.database.transaction(propagation="requires_new") as session:
            result = await session.execute(
                update(model)
                .where(
                    model.id == identifier,
                    model.send_claim_token == attempt.claim_token,
                    model.send_status.in_((status.INIT.code, status.FAILURE.code)),
                )
                .values(send_status=status.SENDING.code, send_claim_until=None)
            )
            if result.rowcount != 1:
                raise DeliveryCancelled("外发领取已失效")
        attempt.stage = DeliveryAttemptStageEnum.REQUEST_STARTED

    async def _finish(
        self, kind: str, identifier: int, attempt: DeliveryAttempt, **values: int | str | None
    ) -> None:
        """按原认领令牌结算并释放租约，令牌变化时保留未知结果错误。"""
        model, _, _ = _CHANNELS[kind]
        async with self.database.transaction(propagation="requires_new") as session:
            result = await session.execute(
                update(model)
                .where(model.id == identifier, model.send_claim_token == attempt.claim_token)
                .values(
                    **values,
                    send_claim_until=None,
                    send_claim_token=None,
                    send_time=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            if result.rowcount != 1:
                raise MessageResultUnknown("外发结果写入时领取已变化")
