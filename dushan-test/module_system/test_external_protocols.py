from types import SimpleNamespace

import aiosmtplib
import httpx
import pytest

from module_system.framework.mail.client.smtp_mail_client import SmtpMailClient
from module_system.framework.mail.model.mail_account import MailAccount
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.framework.notification.delivery.delivery_uncertain_failure import (
    DeliveryUncertainFailure,
)
from module_system.framework.sms.client.providers.aliyun_sms_client import AliyunSmsClient
from module_system.framework.sms.client.providers.debug_ding_talk_sms_client import (
    DebugDingTalkSmsClient,
)
from module_system.framework.sms.client.providers.huawei_sms_client import HuaweiSmsClient
from module_system.framework.sms.client.providers.qiniu_sms_client import QiniuSmsClient
from module_system.framework.sms.client.providers.tencent_sms_client import TencentSmsClient
from module_system.framework.sms.factory.sms_client_factory_impl import SmsClientFactoryImpl
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.framework.social.security.social_auth_config_security import (
    SocialAuthConfigSecurity,
)


@pytest.mark.parametrize(
    "client_type, key, payload",
    [
        (
            AliyunSmsClient,
            "access",
            {"Code": "OK", "BizId": "serial", "RequestId": "request", "Message": "OK"},
        ),
        (DebugDingTalkSmsClient, "access", {"errcode": 0, "errmsg": "ok"}),
        (
            HuaweiSmsClient,
            "access sender",
            {"code": "000000", "result": [{"smsMsgId": "serial", "status": "000000"}]},
        ),
        (QiniuSmsClient, "access", {"message_id": "serial", "request_id": "request"}),
    ],
)
async def test_sms_protocols_use_persisted_boundary_and_native_dto(client_type, key, payload):
    client = client_type(
        SmsChannelProperties(
            id=1, signature="Test", code="test", api_key=key, api_secret="secret", callback_url=None
        )
    )
    await client.http_client.aclose()
    events = []

    async def started():
        events.append("started")

    def respond(request):
        assert events == ["started"]
        events.append("request")
        return httpx.Response(200, json=payload)

    client._http_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        result = await client.send_sms(
            send_log_id=10,
            mobile="13800138000",
            api_template_id="template",
            template_params={"code": "1234"},
            on_request_started=started,
        )
        assert result.success
        assert events == ["started", "request"]
    finally:
        await client.http_client.aclose()


async def test_sms_unknown_response_is_not_retried():
    client = AliyunSmsClient(
        SmsChannelProperties(
            id=1, signature="Test", code="ALIYUN", api_key="access", api_secret="secret"
        )
    )
    await client.http_client.aclose()
    calls = []

    async def started():
        calls.append("started")

    def timeout(request):
        calls.append("request")
        raise httpx.ReadTimeout("unknown", request=request)

    client._http_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    try:
        with pytest.raises(httpx.ReadTimeout):
            await client.send_sms(1, "13800138000", "template", {}, on_request_started=started)
        assert calls == ["started", "request"]
    finally:
        await client.http_client.aclose()


async def test_sms_factory_keeps_provider_and_refreshes_same_channel():
    factory = SmsClientFactoryImpl()
    properties = SmsChannelProperties(
        id=1, signature="Test", code="ALIYUN", api_key="access", api_secret="secret"
    )
    try:
        first = factory.create_or_update_sms_client(properties)
        assert factory.create_or_update_sms_client(properties) is first
        updated = properties.model_copy(update={"api_secret": "rotated"})
        assert factory.create_or_update_sms_client(updated) is first
        assert first.properties.api_secret == "rotated"
        with pytest.raises(ValueError, match="不能更换厂商"):
            factory.create_or_update_sms_client(properties.model_copy(update={"code": "TENCENT"}))
        assert first.properties == updated
        assert factory.get_sms_client_by_code("TENCENT") is None
        assert factory.get_sms_client_by_code("ALIYUN") is first
        second = factory.create_or_update_sms_client(
            properties.model_copy(update={"id": 2, "code": "TENCENT", "api_key": "access sdk-app"})
        )
        assert isinstance(second, TencentSmsClient)
        assert factory.get_sms_client_by_id(1) is first
    finally:
        await factory.close()
    assert first.http_client.is_closed and second.http_client.is_closed


async def test_tencent_sms_sdk_receives_parameters_after_send_boundary(monkeypatch):
    from module_system.framework.sms.client.providers import tencent_sms_client

    events = []

    class SDK:
        def __init__(self, *args):
            pass

        def SendSms(self, request):
            assert events == ["started"]
            assert request.SmsSdkAppId == "sdk-app"
            assert request.TemplateParamSet == ["1234"]
            assert request.PhoneNumberSet == ["13800138000"]
            assert request.SessionContext == "10"
            return SimpleNamespace(
                RequestId="request",
                SendStatusSet=[SimpleNamespace(Code="Ok", SerialNo="serial", Message="ok")],
            )

    async def started():
        events.append("started")

    monkeypatch.setattr(tencent_sms_client.sms_client, "SmsClient", SDK)
    client = TencentSmsClient(
        SmsChannelProperties(
            id=1, signature="Test", code="TENCENT", api_key="access sdk-app", api_secret="secret"
        )
    )
    try:
        result = await client.send_sms(
            10, "13800138000", "template", {"code": "1234"}, on_request_started=started
        )
        assert result.success and result.serial_no == "serial"
    finally:
        await client.http_client.aclose()


@pytest.mark.parametrize(
    "failure, expected",
    [("connect", DeliveryDefiniteFailure), ("data", DeliveryUncertainFailure), (None, None)],
)
async def test_mail_boundary_classifies_failure_and_keeps_bcc_private(
    monkeypatch, failure, expected
):
    events = []

    class SMTP:
        def __init__(self, **kwargs):
            assert kwargs["use_tls"]

        async def connect(self):
            if failure == "connect":
                raise OSError("not connected")

        async def mail(self, sender):
            events.append(sender)

        async def rcpt(self, recipient):
            events.append(recipient)

        async def data(self, payload):
            assert events[-1] == "started"
            assert b"bcc@example.com" not in payload
            if failure == "data":
                raise TimeoutError("result unknown")
            return SimpleNamespace(message="queued as message-id")

        def close(self):
            events.append("closed")

    async def started():
        events.append("started")

    monkeypatch.setattr(aiosmtplib, "SMTP", SMTP)
    account = MailAccount(
        host="smtp.example.com",
        port=465,
        user="user",
        password="secret",
        from_address="sender@example.com",
        ssl_enable=True,
    )
    operation = SmtpMailClient.send_multiple(
        account,
        ["to@example.com"],
        ["cc@example.com"],
        ["bcc@example.com"],
        "Subject",
        "Body",
        on_request_started=started,
    )
    if expected is not None:
        with pytest.raises(expected):
            await operation
    else:
        assert await operation == "message-id"
        assert "bcc@example.com" in events
    assert events[-1] == "closed"


def test_social_credentials_are_preserved_only_server_side():
    existing = {
        "options": {"secretKey": "old-secret", "visible": "old"},
        "credentials": {"private_key": "PRIVATE KEY-----content"},
    }
    public = SocialAuthConfigSecurity.sanitize_auth_config(existing)
    assert public == {"options": {"visible": "old"}}
    merged = SocialAuthConfigSecurity.merge_preserved_auth_config_secrets(
        existing, {"options": {"visible": "new"}}
    )
    assert merged["options"]["secretKey"] == "old-secret"
    assert merged["options"]["visible"] == "new"
    with pytest.raises(ValueError):
        SocialAuthConfigSecurity.validate_auth_config_secret_values({"credentials": {"secret": ""}})
