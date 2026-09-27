from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from framework.common.exception import ServiceException
from module_system.controller.admin.auth.vo.auth_register_req_vo import AuthRegisterReqVO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.auth.auth_admin_auth_service_impl import AuthAdminAuthServiceImpl

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def user_register_enabled():
    return False


async def test_disabled_registration_rejects_before_captcha_or_user_creation():
    service = AuthAdminAuthServiceImpl()
    service.settings = SimpleNamespace(user_register_enabled=False)
    service.captcha_service = SimpleNamespace(verification=AsyncMock())
    service.user_service = SimpleNamespace(register_user=AsyncMock())
    req = AuthRegisterReqVO(username="blockeduser", nickname="Blocked", password="Password123")
    with pytest.raises(ServiceException) as error:
        await service.register(req)
    assert error.value.error_code == ErrorCodeConstants.USER_REGISTER_DISABLED
    service.captcha_service.verification.assert_not_awaited()
    service.user_service.register_user.assert_not_awaited()


async def test_disabled_registration_is_publicly_reported_and_cannot_create_account(
    system_app, system_database
):
    username = "closed" + uuid4().hex[:10]
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        configuration = (await client.get("/admin-api/system/auth/registration-enabled")).json()
        assert configuration["code"] == 0 and configuration["data"] is False
        response = await client.post(
            "/admin-api/system/auth/register",
            headers={"X-Tenant-Id": "1"},
            json={"username": username, "nickname": "Blocked", "password": "Password123"},
        )
        assert response.json()["code"] == ErrorCodeConstants.USER_REGISTER_DISABLED.code
        assert client.cookies.get("system_refresh") is None
    with system_database[2].cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {AdminUserDO.__tablename__} WHERE username = %s", (username,)
        )
        assert cursor.fetchone()[0] == 0
