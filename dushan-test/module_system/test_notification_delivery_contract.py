import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.enums import StatusEnum
from framework.starter_mq.public import MessageResultUnknown
from module_system.definitions.enums.mail.mail_send_status_enum import MailSendStatusEnum
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum
from module_system.framework.notification.delivery.delivery_attempt import DeliveryAttempt
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.framework.notification.delivery.delivery_uncertain_failure import (
    DeliveryUncertainFailure,
)
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.service.notification.notification_delivery_service_impl import (
    NotificationDeliveryServiceImpl,
)
from module_system.service.sms.sms_send_service_impl import SmsSendServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture(
    params=[
        ("mail", MailSendStatusEnum, "send_exception"),
        ("sms", SmsSendStatusEnum, "api_send_msg"),
    ]
)
def delivery_case(request):
    """为两个渠道装配真实共享执行器及隔离持久化替身。"""
    kind, status, error_field = request.param
    delivery = NotificationDeliveryServiceImpl()
    attempt = DeliveryAttempt(claim_token="claim")
    delivery._claim = AsyncMock(return_value=attempt)
    delivery._started = AsyncMock()
    delivery._finish = AsyncMock()
    return delivery, attempt, kind, status, error_field


async def test_delivery_executes_and_settles_provider_result(delivery_case):
    """请求开始回调先于发送结果，渠道字段只在成功返回后结算。"""
    delivery, attempt, kind, status, _ = delivery_case

    async def send(started):
        """模拟完成网络边界并返回渠道结果。"""
        await started()
        delivery._started.assert_awaited_once_with(kind, 12, attempt)
        return "receipt"

    values = {"send_status": status.SUCCESS.code, "receipt": "receipt"}
    result_values = Mock(return_value=values)
    await delivery.execute(kind, 12, send=send, result_values=result_values)
    result_values.assert_called_once_with("receipt")
    delivery._finish.assert_awaited_once_with(kind, 12, attempt, **values)


async def test_terminal_delivery_does_not_resend(delivery_case):
    """已结算的消息跳过外发、回执转换和再次结算。"""
    delivery, _, kind, _, _ = delivery_case
    delivery._claim.return_value = None
    send = AsyncMock()
    result_values = Mock()
    await delivery.execute(kind, 12, send=send, result_values=result_values)
    send.assert_not_awaited()
    result_values.assert_not_called()
    delivery._finish.assert_not_awaited()


@pytest.mark.parametrize("state", ["SUCCESS", "IGNORE", "CANCELLED", "SENDING", "claimed"])
async def test_persistent_state_blocks_duplicate_send(delivery_case, state):
    """真实认领逻辑拒绝终态、结果未知和仍有效的并发认领。"""
    _, _, kind, status, _ = delivery_case
    entry = SimpleNamespace(
        send_status=status.INIT.code if state == "claimed" else getattr(status, state).code,
        send_claim_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1),
    )
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: entry))
    )

    @asynccontextmanager
    async def transaction(**kwargs):
        """提供记录读取替身，不连接数据库。"""
        yield session

    delivery = NotificationDeliveryServiceImpl()
    delivery.database = SimpleNamespace(transaction=transaction)
    send = AsyncMock()
    operation = delivery.execute(kind, 12, send=send, result_values=Mock())
    if state == "SENDING":
        with pytest.raises(MessageResultUnknown):
            await operation
    elif state == "claimed":
        with pytest.raises(DeliveryDefiniteFailure):
            await operation
    else:
        await operation
    send.assert_not_awaited()
    session.execute.assert_awaited_once()


@pytest.mark.parametrize("outcome", ["cancelled", "definite", "unknown"])
async def test_delivery_failure_classification(delivery_case, outcome):
    """取消、明确失败与请求后未知按各渠道字段持久化，保留异常因果。"""
    delivery, attempt, kind, status, error_field = delivery_case
    failure = {
        "cancelled": DeliveryCancelled("不再授权"),
        "definite": DeliveryDefiniteFailure("连接拒绝"),
        "unknown": DeliveryUncertainFailure("请求后断线"),
    }[outcome]

    async def send(started):
        """仅未知结果进入网络请求边界。"""
        if outcome == "unknown":
            await started()
        raise failure

    result_values = Mock()
    operation = delivery.execute(kind, 12, send=send, result_values=result_values)
    if outcome == "cancelled":
        await operation
        values = {"send_status": status.CANCELLED.code}
    elif outcome == "definite":
        with pytest.raises(DeliveryDefiniteFailure) as caught:
            await operation
        assert caught.value is failure
        values = {"send_status": status.FAILURE.code, error_field: type(failure).__name__}
    else:
        with pytest.raises(MessageResultUnknown) as caught:
            await operation
        assert caught.value.__cause__ is failure
        values = {"send_status": status.SENDING.code, error_field: type(failure).__name__}
    delivery._finish.assert_awaited_once_with(kind, 12, attempt, **values)
    result_values.assert_not_called()


@pytest.mark.parametrize("request_started", [False, True])
async def test_task_cancellation_preserves_recovery_state(delivery_case, request_started):
    """任务取消直接传播，不把在途投递结算成业务取消或失败。"""
    delivery, _, kind, _, _ = delivery_case

    async def send(started):
        """在指定网络边界模拟任务取消。"""
        if request_started:
            await started()
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await delivery.execute(kind, 12, send=send, result_values=Mock())
    delivery._finish.assert_not_awaited()
    assert delivery._started.await_count == int(request_started)


async def test_settlement_conflict_is_not_reclassified(delivery_case):
    """外发成功后 CAS 失败保持未知结果，不能再次覆盖结算。"""
    delivery, _, kind, status, _ = delivery_case
    failure = MessageResultUnknown("令牌已变化")
    delivery._finish.side_effect = failure
    with pytest.raises(MessageResultUnknown) as caught:
        await delivery.execute(
            kind,
            12,
            send=AsyncMock(return_value="receipt"),
            result_values=lambda result: {"send_status": status.SUCCESS.code},
        )
    assert caught.value is failure
    assert delivery._finish.await_count == 1


@pytest.mark.parametrize(
    "phase,error_type", [("_started", DeliveryCancelled), ("_finish", MessageResultUnknown)]
)
async def test_persistent_cas_rejects_lost_claim(phase, error_type):
    """数据库 CAS 未更新任何行时，网络边界和结算分别保留规定错误。"""
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(rowcount=0)))

    @asynccontextmanager
    async def transaction(**kwargs):
        """为真实 SQL 构造提供无数据库的事务替身。"""
        assert kwargs == {"propagation": "requires_new"}
        yield session

    delivery = NotificationDeliveryServiceImpl()
    delivery.database = SimpleNamespace(transaction=transaction)
    attempt = DeliveryAttempt(claim_token="claim")
    with pytest.raises(error_type):
        await getattr(delivery, phase)("mail", 12, attempt)
    statement = session.execute.await_args.args[0]
    assert "send_claim_token" in str(statement.whereclause)
    assert "claim" in statement.compile().params.values()


@pytest.mark.parametrize("enabled,accepted", [(True, True), (True, False), (False, True)])
async def test_sms_channel_result_and_disabled_channel(monkeypatch, enabled, accepted):
    """短信厂商结果映射完整，停用渠道在认领后取消且不触发网络请求。"""
    delivery = NotificationDeliveryServiceImpl()
    attempt = DeliveryAttempt(claim_token="claim")
    delivery._claim = AsyncMock(return_value=attempt)
    delivery._started = AsyncMock()
    delivery._finish = AsyncMock()
    result = SmsSendRespDTO(
        success=accepted,
        api_code="code",
        api_msg="message",
        api_request_id="request",
        serial_no="serial",
    )

    async def send_sms(*args, on_request_started):
        """模拟客户端发送前提交请求开始状态。"""
        await on_request_started()
        return result

    client = SimpleNamespace(send_sms=AsyncMock(side_effect=send_sms))
    service = SmsSendServiceImpl()
    service.delivery = delivery
    channel = SimpleNamespace(status=StatusEnum.ENABLE.code if enabled else StatusEnum.DISABLE.code)
    service._validate_sms_channel = AsyncMock(return_value=channel)
    monkeypatch.setattr(SmsChannelProperties, "model_validate", Mock(return_value=channel))
    service.sms_client_factory = SimpleNamespace(
        create_or_update_sms_client=Mock(return_value=client)
    )
    await service.do_send_sms(
        SmsSendMessage(
            message_id="a" * 32,
            log_id=12,
            mobile="13800138000",
            channel_id=1,
            api_template_id="template",
        )
    )
    if enabled:
        delivery._started.assert_awaited_once_with("sms", 12, attempt)
        delivery._finish.assert_awaited_once_with(
            "sms",
            12,
            attempt,
            send_status=SmsSendStatusEnum.SUCCESS.code
            if accepted
            else SmsSendStatusEnum.FAILURE.code,
            api_send_code="code",
            api_send_msg="message",
            api_request_id="request",
            api_serial_no="serial",
        )
    else:
        client.send_sms.assert_not_awaited()
        delivery._started.assert_not_awaited()
        delivery._finish.assert_awaited_once_with(
            "sms", 12, attempt, send_status=SmsSendStatusEnum.CANCELLED.code
        )
