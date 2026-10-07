import json
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from framework.starter_auth.public import AuthErrorCodes, AuthService
from framework.starter_security.public import SecurityErrorCodes
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants

pytestmark = pytest.mark.asyncio(loop_scope="module")
CALLBACK = "https://admin.example.test/auth/social-login"


@pytest.fixture(scope="module")
def auth_enabled():
    return True


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def providers(system_app, admin_client):
    calls = []

    def vendor(request):
        calls.append(request.url.path)
        if request.url.path == "/sns/getuserinfo_bycode":
            assert json.loads(request.content)["tmp_auth_code"].startswith("code-")
            return httpx.Response(
                200, json={"errcode": 0, "user_info": {"openid": "ding-user", "nick": "Ding"}}
            )
        if request.url.path == "/cgi-bin/gettoken":
            return httpx.Response(
                200,
                json={"errcode": 0, "access_token": "application-credential", "expires_in": 7200},
            )
        if request.url.path == "/cgi-bin/user/getuserinfo":
            return httpx.Response(200, json={"errcode": 0, "UserId": "wecom-user"})
        if request.url.path == "/cgi-bin/user/get":
            return httpx.Response(200, json={"errcode": 0, "userid": "wecom-user", "name": "WeCom"})
        raise AssertionError(f"Unexpected vendor path: {request.url.path}")

    application = system_app.state.application_context
    with application.execution():
        auth = application.container.get(AuthService)
        assert auth._http is None
        auth._transport = httpx.MockTransport(vendor)
    for kind, scopes, options in [
        (20, ["snsapi_login"], {}),
        (30, [], {"agent_id": "10001", "lang": "zh"}),
    ]:
        response = await admin_client.post(
            "/admin-api/system/social/client/create",
            json={
                "name": "Provider" + str(kind),
                "socialType": kind,
                "userType": 2,
                "clientId": f"client-{kind}",
                "clientSecret": "test-secret",
                "agentId": "10001",
                "authConfig": {"redirect_uri": CALLBACK, "scopes": scopes, "options": options},
                "status": 1,
            },
        )
        assert response.json()["code"] == 0, response.json()
    return calls


async def begin(client, kind):
    response = await client.post(
        "/admin-api/system/auth/social-auth-redirect",
        params={"type": kind, "redirectUri": CALLBACK},
        headers={"X-Tenant-Id": "1"},
    )
    assert response.json()["code"] == 0, response.json()
    url = urlparse(response.json()["data"])
    assert url.hostname == ("oapi.dingtalk.com" if kind == 20 else "open.work.weixin.qq.com")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    return {"type": kind, "code": "code-" + uuid4().hex, "state": parse_qs(url.query)["state"][0]}


@pytest.mark.parametrize("kind", [20, 30])
async def test_unbound_identity_fresh_authorization_binding_and_next_login(
    system_app, admin_client, system_database, providers, kind
):
    async with AsyncClient(
        transport=ASGITransport(app=system_app, client=(f"127.0.0.{kind}", 1234)),
        base_url="http://testserver",
    ) as client:
        options = await client.get(
            "/admin-api/system/auth/social-providers", headers={"X-Tenant-Id": "1"}
        )
        assert [item["type"] for item in options.json()["data"]] == [20, 30]
        assert "secret" not in options.text and "clientId" not in options.text
        original = await begin(client, kind)
        result = (await client.post("/admin-api/system/auth/social-login", json=original)).json()
        assert result["code"] == ErrorCodeConstants.AUTH_THIRD_LOGIN_NOT_BIND.code, result
        assert client.cookies.get("system_refresh") is None
        before_replay = len(providers)
        assert (await client.post("/admin-api/system/auth/social-login", json=original)).json()[
            "code"
        ] != 0
        assert len(providers) == before_replay

        # 正常密码登录后重新授权，绑定使用当前令牌身份，不复用已消费的 code/state。
        login = (
            await client.post(
                "/admin-api/system/auth/login",
                json={"username": "admin", "password": "admin123"},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert login["code"] == 0, login
        bind = await begin(client, kind)
        assert bind["state"] != original["state"]
        bound = (
            await client.post(
                "/admin-api/system/social/user/bind",
                json=bind,
                headers={"Authorization": "Bearer " + login["data"]["accessToken"]},
            )
        ).json()
        assert bound["code"] == 0, bound
        before_replay = len(providers)
        replay = await client.post(
            "/admin-api/system/social/user/bind",
            json=bind,
            headers={"Authorization": "Bearer " + login["data"]["accessToken"]},
        )
        assert replay.json()["code"] != 0 and len(providers) == before_replay

        credentials = await begin(client, kind)
        result = (await client.post("/admin-api/system/auth/social-login", json=credentials)).json()
        assert result["code"] == 0 and result["data"]["tenantId"] == "1", result
        info = (
            await client.get(
                "/admin-api/system/auth/get-permission-info",
                headers={"Authorization": "Bearer " + result["data"]["accessToken"]},
            )
        ).json()
        assert info["data"]["user"]["username"] == "admin"
        with system_database[2].cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM system_social_user_bind WHERE tenant_id = 1 AND social_type = %s AND deleted = 0",
                (kind,),
            )
            assert cursor.fetchone()[0] == 1


async def test_social_callbacks_reject_wrong_state_browser_and_tenant_header(system_app, providers):
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        data = await begin(client, 20)
        before = len(providers)
        rejected = await client.post(
            "/admin-api/system/auth/social-login", json={**data, "state": "f" * 64}
        )
        assert rejected.json()["code"] == AuthErrorCodes.STATE.code
        rejected = await client.post(
            "/admin-api/system/auth/social-login", json=data, headers={"X-Tenant-Id": "1"}
        )
        assert rejected.json()["code"] == SecurityErrorCodes.DENIED.code
        async with AsyncClient(
            transport=ASGITransport(app=system_app), base_url="http://testserver"
        ) as stranger:
            assert (await stranger.post("/admin-api/system/auth/social-login", json=data)).json()[
                "code"
            ] == SecurityErrorCodes.INVALID.code
            await begin(stranger, 20)
            assert (await stranger.post("/admin-api/system/auth/social-login", json=data)).json()[
                "code"
            ] == AuthErrorCodes.STATE.code
        assert len(providers) == before
        assert (await client.post("/admin-api/system/auth/social-login", json=data)).json()[
            "code"
        ] == 0


async def test_catalog_uses_selected_tenant_and_excludes_disabled_and_non_admin_clients(
    system_app, admin_client, providers
):
    package = (
        await admin_client.post(
            "/admin-api/system/tenant/package/create",
            json={
                "name": "Social" + uuid4().hex[:8],
                "status": 1,
                "menuIds": [],
            },
        )
    ).json()
    assert package["code"] == 0, package
    tenant = (
        await admin_client.post(
            "/admin-api/system/tenant/create",
            json={
                "name": "Social" + uuid4().hex[:8],
                "contactName": "B",
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
    for kind, user, status, config in [
        (20, 1, 1, {"redirect_uri": CALLBACK}),
        (33, 2, 1, {}),
        (32, 2, 0, {"redirect_uri": CALLBACK}),
    ]:
        response = await admin_client.post(
            "/admin-api/system/social/client/create",
            json={
                "name": "Excluded" + str(kind),
                "socialType": kind,
                "userType": user,
                "clientId": "excluded-client",
                "clientSecret": "test-secret",
                "status": status,
                "authConfig": config,
            },
        )
        assert response.json()["code"] == 0, response.json()
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        for tenant_id, expected in [("1", [20, 30]), (tenant["data"], [])]:
            result = (
                await client.get(
                    "/admin-api/system/auth/social-providers", headers={"X-Tenant-Id": tenant_id}
                )
            ).json()
            assert result["code"] == 0 and [item["type"] for item in result["data"]] == expected, (
                result
            )
        assert (await client.get("/admin-api/system/auth/social-providers")).json()["code"] != 0


async def test_vendor_callback_relay_accepts_form_and_query_without_trusting_redirect_input(
    system_app, admin_client, providers
):
    response = await admin_client.post(
        "/admin-api/system/social/client/create",
        json={
            "name": "DingTalk V2",
            "socialType": 46,
            "userType": 2,
            "clientId": "test-v2",
            "clientSecret": "test-v2-secret",
            "status": 1,
            "authConfig": {
                "redirect_uri": "https://api.example.test/admin-api/system/auth/social-callback",
                "frontend_redirect_uri": CALLBACK,
                "scopes": ["openid"],
            },
        },
    )
    assert response.json()["code"] == 0, response.json()
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        result = (
            await client.post(
                "/admin-api/system/auth/social-auth-redirect",
                params={"type": 46, "redirectUri": CALLBACK},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert result["code"] == 0, result
        state = parse_qs(urlparse(result["data"]).query)["state"][0]
        values = {"state": state, "authCode": "code-relay", "redirectUri": "https://evil.example/"}
        # form_post 入站不依赖跨站 Cookie；转回前端后仍须由 social-login 校验原浏览器绑定。
        async with AsyncClient(
            transport=ASGITransport(app=system_app), base_url="http://testserver"
        ) as vendor:
            response = await vendor.post("/admin-api/system/auth/social-callback", data=values)
            assert response.status_code == 303, response.text
            location = urlparse(response.headers["location"])
            assert location.scheme + "://" + location.netloc + location.path == CALLBACK
            assert parse_qs(location.query) == {"state": [state], "authCode": ["code-relay"]}
            assert response.headers["cache-control"] == "no-store"
            assert (
                await vendor.post("/admin-api/system/auth/social-callback", data=values)
            ).status_code != 303

        # 第三方按 OAuth 默认的查询参数方式 GET 重定向到后端回调，同样只转交一次。
        result = (
            await client.post(
                "/admin-api/system/auth/social-auth-redirect",
                params={"type": 46, "redirectUri": CALLBACK},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert result["code"] == 0, result
        state = parse_qs(urlparse(result["data"]).query)["state"][0]
        values = {"state": state, "authCode": "code-query"}
        async with AsyncClient(
            transport=ASGITransport(app=system_app), base_url="http://testserver"
        ) as vendor:
            response = await vendor.get("/admin-api/system/auth/social-callback", params=values)
            assert response.status_code == 303, response.text
            location = urlparse(response.headers["location"])
            assert location.scheme + "://" + location.netloc + location.path == CALLBACK
            assert parse_qs(location.query) == {"state": [state], "authCode": ["code-query"]}
            assert (
                await vendor.get("/admin-api/system/auth/social-callback", params=values)
            ).status_code != 303
