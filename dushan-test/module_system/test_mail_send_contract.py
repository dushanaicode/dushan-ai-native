from datetime import datetime
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiosmtplib
import pytest

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_load_through_coordinator import CacheLoadThroughCoordinator
from framework.starter_di.context.application_context import ApplicationContext
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.framework.mail.client.smtp_mail_client import SmtpMailClient
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.service.mail.bo.mail_batch_dispatch_bo import MailBatchDispatchBO
from module_system.service.mail.bo.mail_dispatch_bo import MailDispatchBO
from module_system.service.mail.mail_account_service_impl import MailAccountServiceImpl
from module_system.service.mail.mail_send_service_impl import MailSendServiceImpl
from module_system.service.mail.mail_template_service_impl import MailTemplateServiceImpl
from module_system.service.notification.notification_delivery_service_impl import (
    NotificationDeliveryServiceImpl,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mail_rows():
    """构造不访问数据库的邮件账号与模板。"""
    audit = dict(
        creator="1",
        updater="1",
        create_time=datetime(2026, 1, 1),
        update_time=datetime(2026, 1, 1),
        deleted=False,
    )
    return (
        MailAccountDO(
            id=1,
            mail="sender@example.com",
            username="sender",
            password="secret",
            host="smtp.example.com",
            port=465,
            ssl_enable=True,
            starttls_enable=False,
            **audit,
        ),
        MailTemplateDO(
            id=2,
            name="邮件模板",
            code="test",
            account_id=1,
            nickname='渡山, "通知"',
            title="标题",
            content="正文",
            params=[],
            status=StatusEnum.ENABLE.code,
            remark=None,
            **audit,
        ),
    )


@pytest.mark.parametrize("batch", [False, True], ids=["single", "batch"])
@pytest.mark.parametrize("publish_failure", [False, True], ids=["published", "failed"])
async def test_mail_publish_propagates_failure_without_result_write(
    mail_rows, batch, publish_failure
):
    """发布失败保留原始异常，事务内不尝试写入失效的外发结果。"""
    account, template = mail_rows
    service = MailSendServiceImpl()
    service.mail_account_service = SimpleNamespace(get_mail_account=AsyncMock(return_value=account))
    service.mail_template_service = SimpleNamespace(
        get_mail_template_by_code=AsyncMock(return_value=template),
        format_mail_template_content=lambda text, params: text,
    )
    failure = RuntimeError("MQ 发布失败")
    service.mail_producer = SimpleNamespace(
        send_mail_message=AsyncMock(side_effect=failure if publish_failure else None)
    )
    service.mail_log_service = SimpleNamespace(
        create_mail_log=AsyncMock(return_value=10),
        create_multiple_mail_log=AsyncMock(return_value=10),
        update_mail_send_result=AsyncMock(side_effect=AssertionError("不应写回结果")),
    )
    values = dict(
        user_id=1, user_type=UserTypeEnum.ADMIN.code, template_code="test", template_params={}
    )
    if batch:
        req = MailBatchDispatchBO(
            to_mails=["recipient@example.com"], cc_mails=None, bcc_mails=None, **values
        )
        operation = MailSendServiceImpl.send_multiple_mail.__wrapped__(service, req)
    else:
        req = MailDispatchBO(mail="recipient@example.com", **values)
        operation = MailSendServiceImpl.send_single_mail.__wrapped__(service, req)
    if publish_failure:
        with pytest.raises(RuntimeError) as error:
            await operation
        assert error.value is failure
    else:
        assert await operation == 10
    service.mail_producer.send_mail_message.assert_awaited_once()
    message = service.mail_producer.send_mail_message.await_args.args[0]
    assert message.log_id == 10
    assert message.to_mails == ["recipient@example.com"]
    service.mail_log_service.update_mail_send_result.assert_not_awaited()


@pytest.mark.parametrize("nickname", [None, "  ", '渡山, "通知"'])
@pytest.mark.parametrize("response, identifier", [("queued as smtp-id", "smtp-id"), ("OK", None)])
async def test_smtp_uses_raw_sender_and_structured_display_name(
    monkeypatch, mail_rows, nickname, response, identifier
):
    """显示名交给邮件头编码，信封地址保持原值，缺失回执编号保持空值。"""
    account, _ = mail_rows
    smtp = SimpleNamespace(
        connect=AsyncMock(),
        mail=AsyncMock(),
        rcpt=AsyncMock(),
        data=AsyncMock(return_value=SimpleNamespace(message=response)),
        close=Mock(),
    )
    monkeypatch.setattr(aiosmtplib, "SMTP", Mock(return_value=smtp))
    result = await SmtpMailClient.send_multiple(
        MailSendServiceImpl._build_mail_account(account, nickname),
        ["recipient@example.com"],
        None,
        ["private@example.com"],
        "标题",
        "正文",
        on_request_started=AsyncMock(),
    )
    assert result == identifier
    smtp.mail.assert_awaited_once_with("sender@example.com")
    message = BytesParser(policy=policy.default).parsebytes(smtp.data.await_args.args[0])
    (sender,) = message["From"].addresses
    assert sender.addr_spec == "sender@example.com"
    assert sender.display_name == ("" if nickname is None else nickname.strip())
    assert "Bcc" not in message
    assert b"private@example.com" not in smtp.data.await_args.args[0]
    smtp.close.assert_called_once()


async def test_mail_delivery_preserves_missing_smtp_identifier(monkeypatch, mail_rows):
    """SMTP 成功但无回执编号时，正常记录成功与空编号。"""
    account, _ = mail_rows
    service = MailSendServiceImpl()
    service.mail_account_service = SimpleNamespace(get_mail_account=AsyncMock(return_value=account))
    attempt = object()
    service.delivery = NotificationDeliveryServiceImpl()
    service.delivery._claim = AsyncMock(return_value=attempt)
    service.delivery._started = AsyncMock()
    service.delivery._finish = AsyncMock()
    monkeypatch.setattr(SmtpMailClient, "send_multiple", AsyncMock(return_value=None))
    await service.do_send_mail(
        MailSendMessage(
            message_id="a" * 32,
            log_id=10,
            account_id=1,
            to_mails=["recipient@example.com"],
            title="标题",
            content="正文",
        )
    )
    service.delivery._finish.assert_awaited_once_with(
        "mail", 10, attempt, send_status=10, send_message_id=None
    )


@pytest.mark.parametrize("kind", ["account", "template"])
@pytest.mark.parametrize("outcome", ["value", "none", "error"])
async def test_mail_cache_only_skips_missing_values(monkeypatch, mail_rows, kind, outcome):
    """真实缓存装饰器仅缓存查询值，缺失与查询异常都不写入。"""
    account, template = mail_rows
    handler = SimpleNamespace(
        build_full_key=Mock(return_value="mail:cache"),
        capture_generation=AsyncMock(return_value="generation"),
        publish_loaded_value=AsyncMock(),
    )

    async def get_or_load(**kwargs):
        """执行缓存未命中的真实回源及发布分支。"""
        return await kwargs["load_and_publish"]()

    components = {
        CacheHandler: handler,
        CacheLoadThroughCoordinator: SimpleNamespace(get_or_load=get_or_load),
    }
    monkeypatch.setattr(
        ApplicationContext, "lookup", classmethod(lambda cls, kind: components[kind])
    )
    row = account if kind == "account" else template
    failure = RuntimeError("查询失败")
    lookup = AsyncMock(
        return_value=row if outcome == "value" else None,
        side_effect=failure if outcome == "error" else None,
    )
    if kind == "account":
        service = MailAccountServiceImpl()
        service.mail_account_mapper = SimpleNamespace(select_by_id=lookup)
        operation = service.get_mail_account_from_cache(1)
    else:
        service = MailTemplateServiceImpl()
        service.mail_template_mapper = SimpleNamespace(select_by_code=lookup)
        operation = service.get_mail_template_by_code_from_cache("test")
    if outcome == "error":
        with pytest.raises(RuntimeError) as error:
            await operation
        assert error.value is failure
    else:
        result = await operation
        if outcome == "value":
            assert result.id == row.id
            handler.publish_loaded_value.assert_awaited_once()
        else:
            assert result is None
    if outcome != "value":
        handler.publish_loaded_value.assert_not_awaited()
