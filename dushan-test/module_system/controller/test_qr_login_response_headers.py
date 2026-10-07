from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Request, Response

from module_system.config.qr_login_settings import QrLoginSettings
from module_system.controller.admin.auth.qr_login_controller import QrLoginController
from module_system.controller.admin.auth.vo.auth.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.qr_login.auth_qr_create_resp_vo import (
    AuthQrCreateRespVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_ticket_req_vo import AuthQrTicketReqVO

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("operation", ["create", "consume"])
async def test_qr_login_sensitive_responses_keep_cookies_and_disable_storage(operation):
    """创建与兑换二维码继续返回令牌和 Cookie，并统一禁止缓存。"""
    binding = "a" * 43
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"origin", b"http://testserver"),
                (b"cookie", f"{QrLoginController.COOKIE}={binding}".encode()),
            ],
        }
    )
    response = Response()
    settings = SimpleNamespace(
        allowed_origins=("http://testserver",),
        refresh_cookie_name="system_refresh",
        refresh_cookie_secure=False,
    )
    created = AuthQrCreateRespVO(
        ticket="b" * 43, code="123456", tenant_id="1", expires_at=1000, poll_interval=2
    )
    login = AuthLoginRespVO(
        user_id="1",
        tenant_id="1",
        access_token="access",
        refresh_token="refresh",
        expires_time=1000,
        refresh_expires_time=2000,
    )
    service = SimpleNamespace(
        create=AsyncMock(return_value=created),
        consume=AsyncMock(return_value=login),
    )

    if operation == "create":
        qr_settings = QrLoginSettings(enabled=True, expire_seconds=300)
        result = await QrLoginController.create.__wrapped__(
            request, response, service, settings, qr_settings
        )
        expected_cookie = QrLoginController.COOKIE
        assert result.data == created
        service.create.assert_awaited_once_with(binding, "http://testserver")
        assert "Max-Age=360" in response.headers["set-cookie"]
    else:
        req = AuthQrTicketReqVO(ticket=created.ticket)
        result = await QrLoginController.consume.__wrapped__(
            request, response, req, service, settings
        )
        expected_cookie = settings.refresh_cookie_name
        assert result.data == login
        service.consume.assert_awaited_once_with(created.ticket, binding, "http://testserver")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["set-cookie"].startswith(expected_cookie + "=")
    assert "httponly" in response.headers["set-cookie"].lower()
