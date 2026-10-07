from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr, create_model

from framework.starter_mq.core.message_codec import MessageCodec
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.definitions.enums.mq_backend import MQBackend
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.publish_command import PublishCommand
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.exception.security_exception import SecurityException


@pytest.fixture
def publish_case():
    """使用真实签发授权逻辑和信封编解码，隔离生命周期与外部凭据存储。"""
    security = SecurityService.__new__(SecurityService)
    security._operation = nullcontext
    security._call = lambda callback: callback()
    security.context = SimpleNamespace(
        current_workload=Mock(return_value=None),
        require=Mock(return_value=SimpleNamespace(realm=SecurityRealm.TENANT, tenant_id="1")),
    )
    security._messages = SimpleNamespace(
        issue=AsyncMock(return_value=b"session-proof"),
        issue_workload=AsyncMock(return_value=b"workload-proof"),
    )
    settings = SimpleNamespace(
        backend=MQBackend.REDIS,
        max_message_bytes=1024,
        max_proof_bytes=1024,
        max_age_seconds=60,
        clock_skew_seconds=1,
        signing_secret=SecretStr("test-only-publish-signing-secret-012345"),
    )
    service = MQService()
    service.runtime = SimpleNamespace(
        phase="ready",
        settings=settings,
        security=security,
        tenant=SimpleNamespace(context=SimpleNamespace(get_required_tenant_id=lambda: "1")),
        monitor=SimpleNamespace(inject=lambda: {}),
        codec=MessageCodec(settings),
    )
    message = create_model("Payload", value=(int, ...))(value=1)
    command = PublishCommand(
        destination="mail:send",
        mode=MessageMode.STREAM,
        message=message,
        workload_capability="system.mail.send",
    )
    return SimpleNamespace(service=service, security=security, command=command)


async def test_session_declaration_keeps_session_authority(publish_case):
    """声明工作负载能力不会升级会话，也不会把该能力写入会话信封。"""
    case = publish_case
    prepared = await case.service.prepare(case.command)
    envelope = prepared.envelope
    assert (envelope.authority, envelope.capability, envelope.tenant_id) == ("session", None, "1")
    case.security._messages.issue.assert_awaited_once_with(
        case.security.context.require.return_value, b'{"value":1}', audience="mail:send"
    )
    case.security._messages.issue_workload.assert_not_awaited()
    codec = case.service.runtime.codec
    assert codec.decode(codec.encode(envelope), "mail:send") == envelope


async def test_workload_declaration_uses_existing_grant(publish_case):
    """工作负载仅传播身份已经拥有的声明能力。"""
    case = publish_case
    identity = SimpleNamespace(tenant_id="1", capabilities=frozenset({"system.mail.send"}))
    case.security.context.current_workload.return_value = identity
    prepared = await case.service.prepare(case.command)
    assert prepared.envelope.authority == "workload"
    assert prepared.envelope.capability == "system.mail.send"
    case.security._messages.issue.assert_not_awaited()
    case.security._messages.issue_workload.assert_awaited_once_with(
        identity, b'{"value":1}', audience="mail:send", capability="system.mail.send"
    )


@pytest.mark.parametrize("declaration", [None, "system.mail.send"])
async def test_workload_without_matching_grant_cannot_publish(publish_case, declaration):
    """缺少能力或声明未授权能力时，在签发凭据前拒绝发布。"""
    case = publish_case
    case.security.context.current_workload.return_value = SimpleNamespace(
        tenant_id="1", capabilities=frozenset({"system.sms.send"})
    )
    command = PublishCommand(
        "mail:send", MessageMode.STREAM, case.command.message, workload_capability=declaration
    )
    with pytest.raises(SecurityException) as caught:
        await case.service.prepare(command)
    assert caught.value.error_code is SecurityErrorCodes.DENIED
    case.security._messages.issue.assert_not_awaited()
    case.security._messages.issue_workload.assert_not_awaited()


async def test_declaration_without_identity_does_not_authorize_publish(publish_case):
    """声明字符串不能代替已认证会话。"""
    case = publish_case
    case.security.context.require.side_effect = SecurityException(SecurityErrorCodes.MISSING)
    with pytest.raises(SecurityException) as caught:
        await case.service.prepare(case.command)
    assert caught.value.error_code is SecurityErrorCodes.MISSING
    case.security._messages.issue.assert_not_awaited()
    case.security._messages.issue_workload.assert_not_awaited()


async def test_platform_session_cannot_use_workload_declaration(publish_case):
    """平台会话仍受原有租户会话签发限制。"""
    case = publish_case
    case.security.context.require.return_value = SimpleNamespace(
        realm=SecurityRealm.PLATFORM, tenant_id=None
    )
    with pytest.raises(SecurityException) as caught:
        await case.service.prepare(case.command)
    assert caught.value.error_code is SecurityErrorCodes.DENIED
    case.security._messages.issue.assert_not_awaited()
    case.security._messages.issue_workload.assert_not_awaited()


@pytest.mark.parametrize("workload", [False, True])
async def test_declaration_preserves_tenant_isolation(publish_case, workload):
    """会话与工作负载都必须匹配当前租户上下文。"""
    case = publish_case
    if workload:
        case.security.context.current_workload.return_value = SimpleNamespace(
            tenant_id="2", capabilities=frozenset({"system.mail.send"})
        )
    else:
        case.security.context.require.return_value.tenant_id = "2"
    with pytest.raises(MQException) as caught:
        await case.service.prepare(case.command)
    assert caught.value.error_code is MQErrorCodes.AUTHENTICATION
