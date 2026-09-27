from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from framework.common.enums import StatusEnum
from framework.starter_data_permission.public import (
    DataPermissionProvider,
    DataPermissionService,
    DataScope,
)
from framework.starter_security.public import SecurityErrorCodes, SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.spi.permission.permission_provider_adapter import PermissionProviderAdapter

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize("change", ["revoke", "disable"])
async def test_no_active_role_keeps_only_self_and_does_not_grant_routes(
    admin_client, system_app, change
):
    suffix = uuid4().hex[:10]
    username = "self" + suffix
    result = (
        await admin_client.post(
            "/admin-api/system/user/create",
            json={
                "username": username,
                "nickname": "Self scope",
                "password": "Password123",
                "postIds": [],
            },
        )
    ).json()
    assert result["code"] == 0, result
    user_id = result["data"]
    result = (
        await admin_client.post(
            "/admin-api/system/permission/role/create",
            json={"name": "Self " + suffix, "code": "self_" + suffix, "sort": 1},
        )
    ).json()
    assert result["code"] == 0, result
    role_id = result["data"]
    result = (
        await admin_client.post(
            "/admin-api/system/permission/assign-user-role",
            json={"userId": user_id, "roleIds": [role_id]},
        )
    ).json()
    assert result["code"] == 0, result
    application = system_app.state.application_context
    database = system_app.state.database
    policy = RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async with AsyncClient(
        transport=ASGITransport(app=system_app, client=("127.0.0.2", 10000)),
        base_url="http://testserver",
    ) as user:
        result = (
            await user.post(
                "/admin-api/system/auth/login",
                json={"username": username, "password": "Password123"},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert result["code"] == 0, result
        token = result["data"]["accessToken"]
        user.headers["Authorization"] = "Bearer " + token
        with application.execution(), database.scope():
            security = application.container.get(SecurityService)
            async with security.authorized(token, policy) as before:
                assert application.container.get(DataPermissionService).current().grant.tenant_all
                async with database.read_session() as session:
                    visible = (await session.scalars(select(AdminUserDO.id))).all()
                assert int(user_id) in visible and len(visible) > 1

        if change == "revoke":
            response = await admin_client.post(
                "/admin-api/system/permission/assign-user-role",
                json={"userId": user_id, "roleIds": []},
            )
        else:
            response = await admin_client.put(
                "/admin-api/system/permission/role/update-status",
                json={"id": role_id, "status": StatusEnum.DISABLE.code},
            )
        assert response.json()["code"] == 0, response.json()
        permissions = (await user.get("/admin-api/system/auth/get-permission-info")).json()
        assert permissions["code"] == 0, permissions
        assert permissions["data"]["roles"] == []

        with application.execution(), database.scope():
            async with security.authorized(token, policy) as identity:
                assert identity.authorization_revision != before.authorization_revision
                provider = application.container.get(DataPermissionProvider)
                assert isinstance(provider, PermissionProviderAdapter)
                assert tuple(rule.scope for rule in await provider.rules(identity)) == (
                    DataScope.SELF,
                )
                grant = application.container.get(DataPermissionService).current().grant
                assert not grant.tenant_all
                assert grant.membership_ids == frozenset({str(user_id)})
                assert grant.department_ids == frozenset()
                async with database.read_session() as session:
                    assert (await session.scalars(select(AdminUserDO.id))).all() == [int(user_id)]
                    assert (await session.scalars(select(AdminUserDO.__table__.c.id))).all() == [
                        int(user_id)
                    ]

        denied = (await user.get("/admin-api/system/user/page")).json()
        assert denied["code"] == SecurityErrorCodes.DENIED.code, denied
