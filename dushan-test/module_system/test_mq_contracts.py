from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from module_system.mq.consumer.mail.mail_send_consumer import MailSendConsumer
from module_system.mq.consumer.sms.sms_send_consumer import SmsSendConsumer
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.mq.producer.mail.mail_producer import MailProducer
from module_system.mq.producer.sms.sms_producer import SmsProducer

MAIL_VALUES = dict(
    message_id="a" * 32,
    log_id=1,
    to_mails=["receiver@example.com"],
    account_id=2,
    title="邮件主题",
    content="邮件正文",
)
SMS_VALUES = dict(
    message_id="b" * 32,
    log_id=3,
    mobile="13800000000",
    channel_id=4,
    api_template_id="template",
)


@pytest.mark.parametrize(
    "model,values,field,error_type",
    [
        (MailSendMessage, MAIL_VALUES, "log_id", "int_type"),
        (MailSendMessage, MAIL_VALUES, "account_id", "int_type"),
        (SmsSendMessage, SMS_VALUES, "log_id", "int_type"),
        (SmsSendMessage, SMS_VALUES, "mobile", "string_type"),
        (SmsSendMessage, SMS_VALUES, "channel_id", "int_type"),
        (SmsSendMessage, SMS_VALUES, "api_template_id", "string_type"),
    ],
)
@pytest.mark.parametrize("missing", [False, True])
def test_required_message_fields_reject_none_and_omission(
    model, values, field, error_type, missing
):
    """模型必填类型仍拒绝空值与字段缺失。"""
    payload = dict(values)
    if missing:
        del payload[field]
    else:
        payload[field] = None
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    assert {error["loc"] for error in caught.value.errors()} == {(field,)}
    expected = "missing" if missing else error_type
    assert {error["type"] for error in caught.value.errors()} == {expected}


@pytest.mark.parametrize("field,value", [("to_mails", []), ("title", ""), ("content", "")])
def test_mail_message_keeps_nonempty_business_validation(field, value):
    """移除重复判空后仍保留非空集合和正文校验。"""
    with pytest.raises(ValidationError) as caught:
        MailSendMessage.model_validate({**MAIL_VALUES, field: value})
    assert {error["loc"] for error in caught.value.errors()} == {(field,)}


@pytest.mark.parametrize(
    "model,values,producer_type,consumer_type,method,capability",
    [
        (
            MailSendMessage,
            MAIL_VALUES,
            MailProducer,
            MailSendConsumer,
            "send_mail_message",
            "system.mail.send",
        ),
        (
            SmsSendMessage,
            SMS_VALUES,
            SmsProducer,
            SmsSendConsumer,
            "send_sms_message",
            "system.sms.send",
        ),
    ],
)
async def test_producer_and_consumer_share_message_route(
    model, values, producer_type, consumer_type, method, capability
):
    """发布入口只声明能力，路由与消费者统一使用消息常量。"""
    message = model.model_validate(values)
    producer = producer_type()
    producer.mq_service = SimpleNamespace(publish_after_commit=AsyncMock())
    await getattr(producer_type, method).__wrapped__(producer, message)
    (command,) = producer.mq_service.publish_after_commit.await_args.args
    assert command.destination == model.stream_key == consumer_type.__mq_consumer__.destination
    assert command.workload_capability == capability
    assert command.message is message
    assert command.message_id == message.message_id
    assert "stream_key" not in message.model_dump()
