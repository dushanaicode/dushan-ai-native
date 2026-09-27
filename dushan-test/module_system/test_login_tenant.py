from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from framework.starter_database.public import AuthenticationReader
from framework.starter_security.public import (
    OpaqueToken,
    SecurityRealm,
    SecurityService,
    SecuritySettings,
)
from framework.starter_tenant.public import TenantException
from framework.starter_web.public import RoutePolicy
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize("tenant_enabled", [True, False], scope="module")
async def test_tenant_login_lifecycle_and_isolation(
    system_app, system_database, admin_client, tenant_enabled
):
    transport = ASGITransport(app=system_app, client=("127.0.0.21", 10000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        config = (await client.get("/admin-api/system/auth/tenants")).json()
        assert config["code"] == 0, config
        assert config["data"]["enabled"] is tenant_enabled
        credentials = {"username": "admin", "password": "admin123"}
        if not tenant_enabled:
            assert config["data"]["tenants"] == []
            login = (await client.post("/admin-api/system/auth/login", json=credentials)).json()
            assert login["code"] == 0, login
            assert login["data"]["tenantId"] == "1"
            client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
            denied = (
                await client.post(
                    "/admin-api/system/auth/login", json=credentials, headers={"X-Tenant-Id": "999"}
                )
            ).json()
            assert denied["code"] != 0
        else:
            missing = (await client.post("/admin-api/system/auth/login", json=credentials)).json()
            assert missing["code"] != 0
            invalid = (
                await client.post(
                    "/admin-api/system/auth/login", json=credentials, headers={"X-Tenant-Id": "01"}
                )
            ).json()
            assert invalid["code"] != 0
            package = (
                await admin_client.post(
                    "/admin-api/system/tenant/package/create",
                    json={"name": "Login" + uuid4().hex[:8], "status": 1, "menuIds": []},
                )
            ).json()
            assert package["code"] == 0, package
            tenant = (
                await admin_client.post(
                    "/admin-api/system/tenant/create",
                    json={
                        "name": "Tenant" + uuid4().hex[:8],
                        "contactName": "Tenant B",
                        "status": 1,
                        "packageId": package["data"],
                        "expireTime": "2099-01-01T00:00:00",
                        "accountCount": 10,
                        "username": "admin",
                        "password": "TenantB123",
                    },
                )
            ).json()
            assert tenant["code"] == 0, tenant
            tenant_id = tenant["data"]
            config = (await client.get("/admin-api/system/auth/tenants")).json()["data"]
            assert {"1", tenant_id} <= {row["id"] for row in config["tenants"]}
            assert all(set(row) == {"id", "name"} for row in config["tenants"])
            wrong = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json=credentials,
                    headers={"X-Tenant-Id": tenant_id},
                )
            ).json()
            assert wrong["code"] != 0
            login = (
                await client.post(
                    "/admin-api/system/auth/login",
                    json={"username": "admin", "password": "TenantB123"},
                    headers={"X-Tenant-Id": tenant_id},
                )
            ).json()
            assert login["code"] == 0, login
            assert login["data"]["tenantId"] == tenant_id
            client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
            info = (await client.get("/admin-api/system/auth/get-permission-info")).json()
            assert info["code"] == 0, info
            assert info["data"]["tenantId"] == tenant_id
            foreign_id = int(info["data"]["user"]["id"])
            database = system_app.state.database
            application = system_app.state.application_context
            policy = RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
            with application.execution(), database.scope():
                security = application.container.get(SecurityService)
                token_a = admin_client.headers["Authorization"].removeprefix("Bearer ")
                settings = application.container.get(SecuritySettings)
                digest_a = OpaqueToken.digest(token_a)
                digest_b = OpaqueToken.digest(login["data"]["accessToken"])
                assert (
                    await AuthenticationReader.token_tenant(
                        database,
                        OAuth2AccessTokenDO,
                        token_digest=digest_b,
                        application_id=settings.application_id,
                        domain="another-domain",
                    )
                    is None
                )
                connection = system_database[2]
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE system_oauth2_access_token SET token_digest=%s WHERE tenant_id=%s AND token_digest=%s",
                        (digest_a, tenant_id, digest_b),
                    )
                try:
                    with pytest.raises(ValueError, match="令牌定位键不唯一"):
                        await AuthenticationReader.token_tenant(
                            database,
                            OAuth2AccessTokenDO,
                            token_digest=digest_a,
                            application_id=settings.application_id,
                            domain=settings.default_domain,
                        )
                finally:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE system_oauth2_access_token SET token_digest=%s WHERE tenant_id=%s AND token_digest=%s",
                            (digest_b, tenant_id, digest_a),
                        )
                async with security.authorized(token_a, policy):
                    async with database.transaction() as session:
                        ids = (await session.scalars(select(AdminUserDO.id))).all()
                        assert foreign_id not in ids
                        with pytest.raises(TenantException, match="写入违反租户归属"):
                            await session.execute(
                                update(AdminUserDO.__table__)
                                .where(AdminUserDO.id == foreign_id)
                                .values(nickname="cross-tenant-write")
                            )
            rejected = (
                await client.get(
                    "/admin-api/system/auth/get-permission-info", headers={"tenant-id": "1"}
                )
            ).json()
            assert rejected["code"] != 0

        refreshed = (
            await client.post(
                "/admin-api/system/auth/refresh-token", headers={"Origin": "http://testserver"}
            )
        ).json()
        assert refreshed["code"] == 0, refreshed
        assert refreshed["data"]["tenantId"] == login["data"]["tenantId"]
        assert refreshed["data"]["accessToken"] != login["data"]["accessToken"]
        client.headers["Authorization"] = "Bearer " + refreshed["data"]["accessToken"]
        assert (await client.get("/admin-api/system/auth/get-permission-info")).json()["code"] == 0

        if tenant_enabled:
            disabled = (
                await admin_client.put(
                    "/admin-api/system/tenant/update-status", json={"id": tenant_id, "status": 0}
                )
            ).json()
            assert disabled["code"] == 0, disabled
            options = (await client.get("/admin-api/system/auth/tenants")).json()["data"]["tenants"]
            assert tenant_id not in {row["id"] for row in options}
            assert (await client.get("/admin-api/system/auth/get-permission-info")).json()[
                "code"
            ] != 0
            assert (
                await client.post(
                    "/admin-api/system/auth/refresh-token", headers={"Origin": "http://testserver"}
                )
            ).json()["code"] != 0

        logout = (
            await client.post(
                "/admin-api/system/auth/logout", headers={"Origin": "http://testserver"}
            )
        ).json()
        assert logout["code"] == 0, logout
        assert client.cookies.get("system_refresh") is None
        assert (await client.get("/admin-api/system/auth/get-permission-info")).json()["code"] != 0
        assert (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()[
            "code"
        ] == 0
