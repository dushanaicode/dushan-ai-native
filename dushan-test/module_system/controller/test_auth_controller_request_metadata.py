import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from framework.starter_security.public import SecurityErrorCodes, SecurityException
from module_system.config.qr_login_settings import QrLoginSettings
from module_system.controller.admin.auth.auth_controller import AuthController
from module_system.controller.admin.auth.auth_cookies import AuthCookies
from module_system.controller.admin.auth.qr_login_controller import QrLoginController
from module_system.controller.admin.auth.vo.qr_login.auth_qr_status_resp_vo import (
    AuthQrStatusRespVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_ticket_req_vo import AuthQrTicketReqVO
from module_system.definitions.enums.auth.qr_login_status_enum import QrLoginStatusEnum
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum

pytestmark = pytest.mark.unit


@pytest.fixture
def settings():
    """提供当前控制器使用的来源与 Cookie 配置。"""
    return SimpleNamespace(
        allowed_origins=("http://testserver",),
        refresh_cookie_name="system_refresh",
        refresh_cookie_secure=False,
    )


def request_with_origin(origin=None, *, cookie=None):
    """构造仅包含来源和可选 Cookie 的请求。"""
    headers = []
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    if cookie is not None:
        headers.append((b"cookie", cookie.encode()))
    return Request({"type": "http", "headers": headers})


def endpoint_app(endpoint, **dependencies):
    """通过真实 FastAPI 依赖解析验证端点，业务依赖使用桩对象。"""
    app = FastAPI()
    app.add_api_route("/endpoint", endpoint, methods=["GET", "POST"])
    parameters = inspect.signature(endpoint).parameters

    def override(value):
        """闭包固定每个依赖的桩对象。"""
        return lambda: value

    for name, dependency in dependencies.items():
        app.dependency_overrides[parameters[name].default.dependency] = override(dependency)
    return app


def test_origin_requirement_keeps_optional_and_required_contracts(settings):
    """可选校验接受缺失来源，必需校验返回来源或抛出原安全异常。"""
    assert AuthCookies.check_origin(request_with_origin(), settings) is None
    assert (
        AuthCookies.require_origin(request_with_origin("http://testserver"), settings)
        == "http://testserver"
    )
    with pytest.raises(SecurityException) as failure:
        AuthCookies.require_origin(request_with_origin(), settings)
    assert failure.value.error_code == SecurityErrorCodes.ORIGIN
    for validate in (AuthCookies.check_origin, AuthCookies.require_origin):
        with pytest.raises(SecurityException) as failure:
            validate(request_with_origin("https://evil.invalid"), settings)
        assert failure.value.error_code == SecurityErrorCodes.ORIGIN


@pytest.mark.parametrize("operation", ["create", "poll", "cancel", "consume"])
@pytest.mark.parametrize("origin", [None, "", "https://evil.invalid"])
async def test_qr_rejects_missing_or_disallowed_origin_before_service(operation, origin, settings):
    """四个浏览器端点都在调用业务服务之前拒绝缺失或非法来源。"""
    service = SimpleNamespace(**{operation: AsyncMock()})
    args = {
        "request": request_with_origin(origin),
        "service": service,
        "settings": settings,
    }
    if operation in {"create", "consume"}:
        args["response"] = Response()
    if operation == "create":
        args["qr_settings"] = QrLoginSettings(enabled=True, expire_seconds=300)
    else:
        args["req"] = AuthQrTicketReqVO(ticket="b" * 43)
    with pytest.raises(SecurityException) as failure:
        await getattr(QrLoginController, operation).__wrapped__(**args)
    assert failure.value.error_code == SecurityErrorCodes.ORIGIN
    getattr(service, operation).assert_not_awaited()


@pytest.mark.parametrize("operation", ["poll", "cancel"])
async def test_qr_forwards_validated_origin_with_browser_binding(operation, settings):
    """轮询与取消传递已验证来源和原浏览器绑定。"""
    binding = "a" * 43
    request = request_with_origin(
        "http://testserver", cookie=f"{QrLoginController.COOKIE}={binding}"
    )
    req = AuthQrTicketReqVO(ticket="b" * 43)
    method = AsyncMock(return_value=AuthQrStatusRespVO(status=QrLoginStatusEnum.WAITING))
    result = await getattr(QrLoginController, operation).__wrapped__(
        request, req, SimpleNamespace(**{operation: method}), settings
    )
    method.assert_awaited_once_with(req.ticket, binding, "http://testserver")
    assert result.code == 0


@pytest.mark.parametrize(
    ("authorization", "secret"),
    [
        (None, None),
        ("Basic abc", None),
        ("Bearer", None),
        ("Bearer ", None),
        ("Bearer token", "token"),
        ("bEaReR mixed-case-token", "mixed-case-token"),
    ],
)
async def test_logout_uses_optional_bearer_dependency(authorization, secret, settings):
    """真实依赖解析只注销有效 Bearer 凭据，其余请求仍幂等清 Cookie。"""
    auth = SimpleNamespace(logout=AsyncMock())
    app = endpoint_app(AuthController.logout, auth=auth, settings=settings)
    headers = {} if authorization is None else {"Authorization": authorization}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/endpoint", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"] is True
    assert 'system_refresh=""' in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
    if secret is None:
        auth.logout.assert_not_awaited()
    else:
        auth.logout.assert_awaited_once_with(secret, LoginLogTypeEnum.LOGOUT_SELF.code)


@pytest.mark.parametrize(
    ("origin", "cookie"),
    [(None, "system_refresh=refresh"), ("https://evil.invalid", None)],
)
async def test_logout_keeps_origin_protection(origin, cookie, settings):
    """携带刷新 Cookie 时要求来源，无 Cookie 时仍拒绝显式非法来源。"""
    auth = SimpleNamespace(logout=AsyncMock())
    with pytest.raises(SecurityException) as failure:
        await AuthController.logout(
            request_with_origin(origin, cookie=cookie), Response(), auth, settings, None
        )
    assert failure.value.error_code == SecurityErrorCodes.ORIGIN
    auth.logout.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_social_callback_preserves_redirect_and_security_headers(method):
    """查询与表单回调都保留重复参数、303 跳转、禁止缓存和禁止引用来源。"""
    url = "http://testserver/social-callback?state=state&code=code"
    clients = SimpleNamespace(relay_callback=AsyncMock(return_value=url))
    app = endpoint_app(AuthController.social_callback, clients=clients)
    parameters = "state=state&code=code&state=duplicate"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        if method == "GET":
            response = await client.get(f"/endpoint?{parameters}")
        else:
            response = await client.post(
                "/endpoint",
                content=parameters,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    clients.relay_callback.assert_awaited_once_with(
        [("state", "state"), ("code", "code"), ("state", "duplicate")]
    )
    assert response.status_code == 303
    assert response.headers["location"] == url
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
