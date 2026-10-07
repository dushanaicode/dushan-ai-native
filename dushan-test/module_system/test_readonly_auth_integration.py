from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from framework.starter_cache.public import CacheHandler
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.auth.bo.email_reset_state_bo import EmailResetStateBO
from module_system.service.sms.sms_code_service_impl import SmsCodeServiceImpl
from module_system.service.social.social_user_service_impl import SocialUserServiceImpl
from module_system.service.workload.system_workload_service import SystemWorkloadService

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize("operation", ["sms", "email", "login-binding"])
async def test_anonymous_readonly_account_mutations_are_denied_before_persistence(
    system_app, system_database, monkeypatch, operation
):
    """真实公开路由及主库角色查询不得依赖请求提供 Bearer 或角色。"""
    connection = system_database[2]
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE system_users SET mobile='13800000009',email='demo@example.test' "
            "WHERE username='demo' AND tenant_id='1'"
        )
        cursor.execute(
            "SELECT id,password,credential_revision FROM system_users "
            "WHERE username='demo' AND tenant_id='1'"
        )
        user_id, password, revision = cursor.fetchone()
    social_authorization = AsyncMock()
    monkeypatch.setattr(SocialUserServiceImpl, "_auth_social_user", social_authorization)
    monkeypatch.setattr(SmsCodeServiceImpl, "use_sms_code", AsyncMock())
    if operation == "email":
        application, database = system_app.state.application_context, system_app.state.database
        with application.execution(), database.scope():
            async with application.container.get(SystemWorkloadService).scope("system.auth", "1"):
                auth = application.container.get(AuthAdminAuthService)
                identifier = auth._email_identifier("demo@example.test")
                now = datetime.now(timezone.utc).timestamp()
                state = EmailResetStateBO(
                    code_digest=auth._email_code_digest(identifier, "123456"),
                    user_id=user_id,
                    credential_revision=revision,
                    issued_at=now,
                    expires_at=now + 600,
                    attempts=0,
                    daily_count=1,
                )
                await application.container.get(CacheHandler).set(
                    SystemCacheKeyConstants.EMAIL_PASSWORD_RESET,
                    identifier,
                    state.model_dump(by_alias=False),
                )
    if operation == "login-binding":
        path = "login"
        body = {
            "username": "demo",
            "password": "demo123456",
            "socialType": 10,
            "socialCode": "visitor-oauth-code",
            "socialState": "valid-state",
        }
    else:
        path = "reset-password"
        body = {
            "channel": operation,
            "mobile" if operation == "sms" else "email": "13800000009"
            if operation == "sms"
            else "demo@example.test",
            "code": "123456",
            "password": "Changed123",
        }
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/admin-api/system/auth/" + path, json=body, headers={"X-Tenant-Id": "1"}
        )
    assert response.json()["code"] == 901, response.text
    social_authorization.assert_not_awaited()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT password,credential_revision FROM system_users WHERE id=%s", (user_id,)
        )
        assert cursor.fetchone() == (password, revision)
