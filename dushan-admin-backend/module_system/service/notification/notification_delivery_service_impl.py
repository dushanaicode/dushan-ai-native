from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
from module_system.definitions.enums.notification.delivery_attempt_stage_enum import (
    DeliveryAttemptStageEnum,
)
from module_system.framework.notification.config.notification_delivery_settings import (
    NotificationDeliverySettings,
)
from module_system.framework.notification.delivery.delivery_attempt import DeliveryAttempt
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.service.notification.notification_delivery_service import (
    NotificationDeliveryService,
)


@service(interface=NotificationDeliveryService)
class NotificationDeliveryServiceImpl(NotificationDeliveryService):
    database: SessionProvider = Inject()
    settings: NotificationDeliverySettings = Inject()

    async def claim(self, kind: str, identifier: int) -> DeliveryAttempt | None:
        model = {"mail": MailLogDO, "sms": SmsLogDO}[kind]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with self.database.transaction(propagation="requires_new") as session:
            entry = (
                await session.execute(select(model).where(model.id == identifier).with_for_update())
            ).scalar_one()
            if entry.send_status in {10, 30, 40}:
                return None
            if entry.send_status == 5:
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

    async def started(self, kind: str, identifier: int, attempt: DeliveryAttempt):
        model = {"mail": MailLogDO, "sms": SmsLogDO}[kind]
        async with self.database.transaction(propagation="requires_new") as session:
            result = await session.execute(
                update(model)
                .where(
                    model.id == identifier,
                    model.send_claim_token == attempt.claim_token,
                    model.send_status.in_((0, 20)),
                )
                .values(send_status=5, send_claim_until=None)
            )
            if result.rowcount != 1:
                raise DeliveryCancelled("外发领取已失效")
        attempt.stage = DeliveryAttemptStageEnum.REQUEST_STARTED

    async def finish(self, kind: str, identifier: int, attempt: DeliveryAttempt, **values):
        model = {"mail": MailLogDO, "sms": SmsLogDO}[kind]
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
