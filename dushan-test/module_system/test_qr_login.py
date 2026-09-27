import asyncio
import hashlib
import json
from itertools import count
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from framework.starter_cache.public import CacheHandler
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants

pytestmark = pytest.mark.asyncio(loop_scope="module")
BASE = "/admin-api/system/auth/qr-login"
IPS = count(30)


def browser(app):
    return AsyncClient(
        transport=ASGITransport(app=app, client=(f"127.0.0.{next(IPS)}", 12345)),
        base_url="http://testserver",
        headers={"Origin": "http://testserver", "User-Agent": "Mozilla/5.0 QR-Login-Test"},
    )


def value(response):
    body = response.json()
    assert body["code"] == 0, body
    return body["data"]


async def begin(computer, tenant="1"):
    response = await computer.post(BASE + "/create", headers={"X-Tenant-Id": tenant})
    result = value(response)
    assert len(result["ticket"]) == 43 and len(result["code"]) == 6
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "binding" not in result and "accessToken" not in result
    return {"ticket": result["ticket"]}


async def approve(phone, ticket):
    scan = value(await phone.post(BASE + "/scan", json=ticket))
    assert scan["status"] == "scanned"
    value(await phone.post(BASE + "/confirm", json={**ticket, "approve": True}))


async def test_qr_login_real_tokens_cookie_permissions_and_refresh(
    system_app, admin_client, system_database
):
    async with browser(system_app) as computer:
        ticket = await begin(computer)
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "waiting"
        await approve(admin_client, ticket)
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "approved"
        response = await computer.post(BASE + "/consume", json=ticket)
        login = value(response)
        assert login["tenantId"] == "1" and login["accessToken"]
        assert "refreshToken" not in login and "system_refresh=" in response.headers["set-cookie"]
        computer.headers["Authorization"] = "Bearer " + login["accessToken"]
        permission = value(await computer.get("/admin-api/system/auth/get-permission-info"))
        assert permission["user"]["username"] == "admin"
        computer.headers.pop("Authorization")
        assert (
            value(await computer.post("/admin-api/system/auth/refresh-token"))["accessToken"]
            != login["accessToken"]
        )
        _, _, db = system_database
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM system_login_log WHERE log_type=5 AND user_ip='127.0.0.30'"
            )
            assert cursor.fetchone()[0] == 1


async def test_qr_bound_to_browser_origin_and_authenticated_phone(system_app, admin_client):
    async with browser(system_app) as computer, browser(system_app) as other:
        ticket = await begin(computer)
        assert (await other.post(BASE + "/scan", json=ticket)).json()["code"] != 0
        assert (await other.post(BASE + "/confirm", json={**ticket, "approve": True})).json()[
            "code"
        ] != 0
        assert (await other.post(BASE + "/poll", json=ticket)).json()["code"] != 0
        assert (
            await computer.post(
                BASE + "/poll", json=ticket, headers={"Origin": "https://evil.invalid"}
            )
        ).json()["code"] != 0
        await approve(admin_client, ticket)
        assert (await other.post(BASE + "/consume", json=ticket)).json()["code"] != 0
        assert value(await computer.post(BASE + "/consume", json=ticket))["accessToken"]


async def test_qr_concurrent_consume_is_single_use(system_app, admin_client):
    async with browser(system_app) as computer:
        ticket = await begin(computer)
        await approve(admin_client, ticket)
        results = await asyncio.gather(
            *(computer.post(BASE + "/consume", json=ticket) for _ in range(3))
        )
        assert sum(response.json()["code"] == 0 for response in results) == 1
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "expired"


async def test_qr_cancel_and_expire_cannot_login(system_app, admin_client):
    async with browser(system_app) as computer:
        ticket = await begin(computer)
        value(await admin_client.post(BASE + "/scan", json=ticket))
        value(await admin_client.post(BASE + "/confirm", json={**ticket, "approve": False}))
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "cancelled"
        assert (await computer.post(BASE + "/consume", json=ticket)).json()["code"] != 0
        ticket = await begin(computer)
        value(await computer.post(BASE + "/cancel", json=ticket))
        assert (await admin_client.post(BASE + "/scan", json=ticket)).json()["code"] != 0
        ticket = await begin(computer)
        application = system_app.state.application_context
        with application.execution():
            cache = application.container.get(CacheHandler)
            await cache.eval_atomic(
                SystemCacheKeys.QR_LOGIN,
                (hashlib.sha256(ticket["ticket"].encode()).hexdigest(),),
                "return redis.call('PEXPIRE', KEYS[1], 1)",
            )
        await asyncio.sleep(0.02)
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "expired"
        assert (await admin_client.post(BASE + "/scan", json=ticket)).json()[
            "code"
        ] == ErrorCodeConstants.AUTH_QR_EXPIRED.code


async def test_qr_revoked_approver_cannot_issue_computer_token(system_app):
    async with browser(system_app) as computer, browser(system_app) as phone:
        login = value(
            await phone.post(
                "/admin-api/system/auth/login",
                headers={"X-Tenant-Id": "1"},
                json={"username": "admin", "password": "admin123"},
            )
        )
        phone.headers["Authorization"] = "Bearer " + login["accessToken"]
        ticket = await begin(computer)
        await approve(phone, ticket)
        value(await phone.post("/admin-api/system/auth/logout"))
        assert (await computer.post(BASE + "/consume", json=ticket)).json()[
            "code"
        ] == ErrorCodeConstants.AUTH_QR_IDENTITY_CHANGED.code


async def test_qr_disabled_account_cannot_complete_approved_ticket(
    system_app, admin_client, system_database
):
    async with browser(system_app) as computer:
        ticket = await begin(computer)
        await approve(admin_client, ticket)
        _, _, db = system_database
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE system_users SET status=0 WHERE username='admin' AND tenant_id='1'"
                )
            assert (await computer.post(BASE + "/consume", json=ticket)).json()[
                "code"
            ] == ErrorCodeConstants.AUTH_QR_IDENTITY_CHANGED.code
        finally:
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE system_users SET status=1 WHERE username='admin' AND tenant_id='1'"
                )


async def test_qr_tenant_isolation(system_app, admin_client):
    package = value(
        await admin_client.post(
            "/admin-api/system/tenant/package/create",
            json={"name": "QR" + uuid4().hex[:8], "status": 1, "menuIds": []},
        )
    )
    tenant = value(
        await admin_client.post(
            "/admin-api/system/tenant/create",
            json={
                "name": "QR" + uuid4().hex[:8],
                "contactName": "QR tenant",
                "status": 1,
                "packageId": package,
                "expireTime": "2099-01-01T00:00:00",
                "accountCount": 10,
                "username": "qradmin",
                "password": "QrTenant123",
            },
        )
    )
    async with browser(system_app) as computer:
        ticket = await begin(computer, tenant)
        assert (await admin_client.post(BASE + "/scan", json=ticket)).json()[
            "code"
        ] == ErrorCodeConstants.AUTH_QR_TENANT.code
        assert value(await computer.post(BASE + "/poll", json=ticket))["status"] == "waiting"


async def test_qr_does_not_expand_mobile_token_scopes(system_app, system_database):
    async with browser(system_app) as computer, browser(system_app) as phone:
        login = value(
            await phone.post(
                "/admin-api/system/auth/login",
                headers={"X-Tenant-Id": "1"},
                json={"username": "admin", "password": "admin123"},
            )
        )
        phone.headers["Authorization"] = "Bearer " + login["accessToken"]
        _, _, db = system_database
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE system_oauth2_access_token SET scopes='[]' WHERE token_digest=%s",
                (hashlib.sha256(login["accessToken"].encode()).hexdigest(),),
            )
        ticket = await begin(computer)
        await approve(phone, ticket)
        result = value(await computer.post(BASE + "/consume", json=ticket))
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT scopes FROM system_oauth2_access_token WHERE token_digest=%s",
                (hashlib.sha256(result["accessToken"].encode()).hexdigest(),),
            )
            assert json.loads(cursor.fetchone()[0]) == []


async def test_qr_restricted_business_scope_can_login_and_update_connection(
    system_app, admin_client, system_database
):
    suffix = uuid4().hex[:8]
    username = "qruser" + suffix
    user_id = value(
        await admin_client.post(
            "/admin-api/system/user/create",
            json={"username": username, "password": "QrUser123", "nickname": "QR user"},
        )
    )
    role_id = value(
        await admin_client.post(
            "/admin-api/system/permission/role/create",
            json={"name": "QR" + suffix, "code": "qr_" + suffix, "sort": 10},
        )
    )
    departments = value(await admin_client.get("/admin-api/system/dept/simple-list"))
    value(
        await admin_client.post(
            "/admin-api/system/permission/assign-role-data-scope",
            json={"roleId": role_id, "dataScope": 2, "dataScopeDeptIds": [departments[0]["id"]]},
        )
    )
    value(
        await admin_client.post(
            "/admin-api/system/permission/assign-user-role",
            json={"userId": user_id, "roleIds": [role_id]},
        )
    )
    async with browser(system_app) as computer, browser(system_app) as phone:
        login = value(
            await phone.post(
                "/admin-api/system/auth/login",
                headers={"X-Tenant-Id": "1"},
                json={"username": username, "password": "QrUser123"},
            )
        )
        phone.headers["Authorization"] = "Bearer " + login["accessToken"]
        ticket = await begin(computer)
        scanned = value(await phone.post(BASE + "/scan", json=ticket))
        value(await phone.post(BASE + "/confirm", json={**ticket, "approve": True}))
        assert value(await computer.post(BASE + "/consume", json=ticket))["accessToken"]
        _, _, db = system_database
        with db.cursor() as cursor:
            cursor.execute("SELECT login_ip FROM system_users WHERE id=%s", (user_id,))
            assert cursor.fetchone()[0] == scanned["ip"]


@pytest.mark.parametrize("qr_login_enabled", [False], scope="module", indirect=True)
async def test_qr_feature_switch_blocks_direct_calls(system_app, admin_client, qr_login_enabled):
    async with browser(system_app) as computer:
        assert value(await computer.get(BASE + "/enabled")) is False
        assert (await computer.post(BASE + "/create", headers={"X-Tenant-Id": "1"})).json()[
            "code"
        ] == ErrorCodeConstants.AUTH_QR_DISABLED.code
        assert (await admin_client.post(BASE + "/scan", json={"ticket": "a" * 43})).json()[
            "code"
        ] == ErrorCodeConstants.AUTH_QR_DISABLED.code
