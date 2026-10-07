from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
from starlette.requests import HTTPConnection

from framework.common.enums import UserTypeEnum
from framework.starter_web.public import RequestContext
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.config.qr_login_settings import QrLoginSettings
from module_system.controller.admin.auth.vo.auth.auth_bind_mobile_req_vo import AuthBindMobileReqVO
from module_system.controller.admin.auth.vo.auth.auth_bind_mobile_sms_send_req_vo import (
    AuthBindMobileSmsSendReqVO,
)
from module_system.controller.admin.auth.vo.auth.auth_recovery_send_req_vo import (
    AuthRecoverySendReqVO,
)
from module_system.controller.admin.auth.vo.auth.auth_reset_password_req_vo import (
    AuthResetPasswordReqVO,
)
from module_system.controller.admin.auth.vo.auth.auth_sms_login_req_vo import AuthSmsLoginReqVO
from module_system.controller.admin.auth.vo.auth.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.definitions.enums.logger.logger_login_result_enum import LoggerLoginResultEnum
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum
from module_system.service.auth.auth_admin_auth_service_impl import AuthAdminAuthServiceImpl
from module_system.service.auth.bo.qr_login_state_bo import QrLoginStateBO
from module_system.service.auth.qr_login_service_impl import QrLoginServiceImpl

pytestmark = pytest.mark.unit


def request(user_agent=None):
    """创建只包含请求元数据的连接，不启动服务器。"""
    headers = [] if user_agent is None else [(b"user-agent", user_agent.encode())]
    return HTTPConnection({"type": "http", "headers": headers})


def login_log(**values):
    """构造登录日志必填数据，供字段边界验证。"""
    return LoginLogCreateReqDTO(
        **{
            "log_type": LoginLogTypeEnum.LOGIN_USERNAME.code,
            "username": "admin",
            "user_type": UserTypeEnum.ADMIN.code,
            "result": LoggerLoginResultEnum.SUCCESS.code,
            "user_ip": "192.0.2.1",
            **values,
        }
    )


@pytest.mark.parametrize("user_agent", [None, "", "A" * 512, "A" * 513])
def test_login_log_limits_user_agent_during_creation_and_assignment(user_agent):
    """所有调用方与赋值路径都受同一日志长度约束。"""
    expected = None if user_agent is None else user_agent[:512]
    value = login_log(user_agent=user_agent)
    assert value.user_agent == expected
    value.user_agent = "B" * 600
    assert value.user_agent == "B" * 512


@pytest.mark.parametrize("user_ip", [None, ""])
def test_login_log_still_rejects_missing_or_empty_ip(user_ip):
    """收口请求信息后仍禁止空的审计地址。"""
    with pytest.raises(ValidationError):
        login_log(user_ip=user_ip)


@pytest.fixture
def auth():
    """只替换外部业务依赖，执行真实认证日志与短信参数构造。"""
    service = AuthAdminAuthServiceImpl()
    service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "1")
    service.login_log_service = SimpleNamespace(create_login_log=AsyncMock())
    service.user_service = SimpleNamespace(
        update_user_login=AsyncMock(),
        get_user=AsyncMock(return_value=SimpleNamespace(id=7)),
        update_user_profile=AsyncMock(),
        change_password=AsyncMock(),
    )
    service.authentication = SimpleNamespace(
        user_by_id=AsyncMock(return_value=SimpleNamespace(id=7, username="admin")),
        user_by_mobile=AsyncMock(return_value=SimpleNamespace(id=7)),
    )
    service.captcha_service = SimpleNamespace(verification=AsyncMock(return_value=True))
    service.sms_code_service = SimpleNamespace(
        send_sms_code=AsyncMock(return_value=6), use_sms_code=AsyncMock()
    )
    service.permission_service = SimpleNamespace(
        has_any_roles=AsyncMock(return_value=False), require_user_writable=AsyncMock()
    )
    service._create_token_after_login_success = AsyncMock()
    return service


@pytest.mark.parametrize("user_agent", [None, "", "A" * 700])
@pytest.mark.parametrize("logout", [False, True])
async def test_auth_log_uses_resolved_metadata_and_dto_length_limit(auth, user_agent, logout):
    """登录与退出使用同一请求投影，成功登录仍更新最后登录地址。"""
    with RequestContext.bind(request(user_agent), "trace-1", "2001:db8::1"):
        if logout:
            await auth._create_logout_log(
                7, UserTypeEnum.ADMIN.code, LoginLogTypeEnum.LOGOUT_SELF.code
            )
        else:
            await auth._create_login_log(
                7, "admin", LoginLogTypeEnum.LOGIN_USERNAME.code, LoggerLoginResultEnum.SUCCESS.code
            )
    (value,) = auth.login_log_service.create_login_log.call_args.args
    assert value.user_agent == ("" if user_agent is None else user_agent[:512])
    assert value.user_ip == "2001:db8::1"
    assert value.trace_id == "trace-1"
    if logout:
        auth.user_service.update_user_login.assert_not_awaited()
    else:
        auth.user_service.update_user_login.assert_awaited_once_with(7, "2001:db8::1")


@pytest.mark.parametrize("logout", [False, True])
async def test_auth_logs_reject_missing_ip_before_persistence(auth, logout):
    """缺失地址在请求适配边界报错，不再等待日志 DTO 拒绝空串。"""
    with RequestContext.bind(request(), "trace-1", None):
        with pytest.raises(RuntimeError, match="缺少客户端 IP"):
            if logout:
                await auth._create_logout_log(
                    7, UserTypeEnum.ADMIN.code, LoginLogTypeEnum.LOGOUT_SELF.code
                )
            else:
                await auth._create_login_log(
                    7,
                    "admin",
                    LoginLogTypeEnum.LOGIN_USERNAME.code,
                    LoggerLoginResultEnum.SUCCESS.code,
                )
    auth.login_log_service.create_login_log.assert_not_awaited()
    auth.user_service.update_user_login.assert_not_awaited()


@pytest.mark.parametrize("client_ip", [None, "192.0.2.1"])
@pytest.mark.parametrize("operation", ["send", "send_bind", "use", "bind", "recover", "reset"])
async def test_sms_flows_require_and_forward_resolved_ip(auth, operation, client_ip):
    """六个验证码入口统一拒绝缺失 IP，正常时原样传给短信服务。"""
    if operation == "send":
        call = auth.send_sms_code(
            AuthSmsSendReqVO(mobile="13800000000", scene=SmsSceneEnum.ADMIN_MEMBER_LOGIN.code)
        )
    elif operation == "send_bind":
        call = auth.send_bind_mobile_code(AuthBindMobileSmsSendReqVO(mobile="13800000000"))
    elif operation == "use":
        call = auth.sms_login(AuthSmsLoginReqVO(mobile="13800000000", code="123456"))
    elif operation == "bind":
        call = auth.bind_mobile(7, AuthBindMobileReqVO(mobile="13800000000", code="123456"))
    elif operation == "recover":
        call = auth.send_recovery_code(AuthRecoverySendReqVO(channel="sms", mobile="13800000000"))
    else:
        call = unwrap(AuthAdminAuthServiceImpl._reset_sms_password)(
            auth,
            AuthResetPasswordReqVO(
                channel="sms", mobile="13800000000", code="123456", password="NewPass123!"
            ),
        )
    with RequestContext.bind(request(), "trace-1", client_ip):
        if client_ip is None:
            with pytest.raises(RuntimeError, match="缺少客户端 IP"):
                await call
            auth.sms_code_service.send_sms_code.assert_not_awaited()
            auth.sms_code_service.use_sms_code.assert_not_awaited()
        else:
            await call
            sending = operation in {"send", "send_bind", "recover"}
            method = (
                auth.sms_code_service.send_sms_code
                if sending
                else auth.sms_code_service.use_sms_code
            )
            (value,) = method.call_args.args
            assert (value.create_ip if sending else value.used_ip) == client_ip


@pytest.mark.parametrize("client_ip", [None, "192.0.2.1"])
@pytest.mark.parametrize("user_agent", [None, "", "A" * 700])
async def test_qr_creation_preserves_optional_display_ip_and_bounded_agent(
    client_ip, user_agent, monkeypatch
):
    """扫码只展示地址，缺失时仍允许创建，浏览器解析输入保持 512 字符上限。"""
    service = QrLoginServiceImpl()
    service.settings = QrLoginSettings(enabled=True, expire_seconds=120)
    service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "1")
    service.cache = SimpleNamespace(eval_atomic=AsyncMock(return_value="OK"))
    parse = Mock(
        return_value=SimpleNamespace(
            browser=SimpleNamespace(family="Browser", version_string="1"),
            os=SimpleNamespace(family="OS"),
        )
    )
    monkeypatch.setattr("module_system.service.auth.qr_login_service_impl.parse_user_agent", parse)
    with RequestContext.bind(request(user_agent), "trace-1", client_ip):
        result = await service.create("binding", "https://example.test")
    _, _, _, (raw, expires) = service.cache.eval_atomic.call_args.args
    state = QrLoginStateBO.model_validate_json(raw)
    assert state.ip == ("" if client_ip is None else client_ip)
    assert state.browser == "Browser 1 · OS"
    assert state.code == result.code
    assert expires == service.settings.expire_seconds
    parse.assert_called_once_with("" if user_agent is None else user_agent[:512])
