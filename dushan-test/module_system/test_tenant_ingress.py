import asyncio
import hashlib
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, Request
from httpx import ASGITransport, AsyncClient
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

from framework.starter_cache.public import CacheHandler
from framework.starter_di.public import DiDependency
from framework.starter_security.public import SecurityErrorCodes, SecurityException
from framework.starter_tenant.public import TenantContext, TenantException
from framework.starter_web.public import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.definitions.constants.public_context_constants import PublicContextConstants
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.service.auth.auth_admin_auth_service_impl import AuthAdminAuthServiceImpl

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def probes():
    return {"frames": [], "background": [], "entered": asyncio.Event(), "release": asyncio.Event()}


@pytest.fixture(scope="module")
def system_routers(probes):
    router = APIRouter(prefix="/test/tenant")

    @router.get("/lifecycle")
    @RoutePolicy.public(context=PublicContextConstants.TENANT_SELECTION)
    async def lifecycle(
        request: Request, context: TenantContext = Depends(DiDependency(TenantContext))
    ):
        frame = context.current()
        probes["frames"].append(frame)
        if request.query_params.get("wait") == "yes":
            probes["entered"].set()
            await probes["release"].wait()
        if request.query_params.get("fail") == "yes":
            raise SecurityException(SecurityErrorCodes.DENIED)

        async def background():
            probes["background"].append(context.current())
            assert context.current().active

        return JSONResponse(
            {"tenant": context.get_required_tenant_id()}, background=BackgroundTask(background)
        )

    return (RouterRegistration(router),)


async def create_tenant(admin_client):
    package = (
        await admin_client.post(
            "/admin-api/system/tenant/package/create",
            json={"name": "Ingress" + uuid4().hex[:8], "status": 1, "menuIds": []},
        )
    ).json()
    assert package["code"] == 0, package
    tenant = (
        await admin_client.post(
            "/admin-api/system/tenant/create",
            json={
                "name": "Ingress" + uuid4().hex[:8],
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
    return tenant["data"]


async def test_tenant_header_is_only_accepted_by_declared_routes(system_app, admin_client):
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        credentials = {"username": "admin", "password": "admin123"}
        for headers in (
            {},
            {"X-Tenant-Id": "01"},
            {"X-Tenant-Id": "0"},
            [("X-Tenant-Id", "1"), ("X-Tenant-Id", "1")],
        ):
            response = (
                await client.post("/admin-api/system/auth/login", json=credentials, headers=headers)
            ).json()
            assert response["code"] != 0, response
        old_body = (
            await client.post(
                "/admin-api/system/auth/login",
                json={**credentials, "tenantId": "1"},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert old_body["code"] == 422, old_body
        assert (
            await client.get("/admin-api/system/auth/tenants", headers={"X-Tenant-Id": "1"})
        ).json()["code"] != 0
        assert (await client.get("/admin-api/system/auth/tenants")).json()["code"] == 0
        override = (
            await admin_client.get(
                "/admin-api/system/auth/get-permission-info", headers={"X-Tenant-Id": "1"}
            )
        ).json()
        assert override["code"] == SecurityErrorCodes.DENIED.code
        document = (await client.get("/openapi.json")).json()
        listed = {
            (method, path)
            for path, methods in document["paths"].items()
            for method, operation in methods.items()
            if path.startswith("/admin-api/system/auth/")
            and operation.get("x-route-access", {}).get("public_context")
            == PublicContextConstants.TENANT_SELECTION
        }
        assert listed == {
            ("post", "/admin-api/system/auth/" + name)
            for name in (
                "login",
                "sms-login",
                "register",
                "send-sms-code",
                "send-password-reset-code",
                "reset-password",
                "qr-login/create",
            )
        } | {
            ("post", "/admin-api/system/auth/social-auth-redirect"),
            ("get", "/admin-api/system/auth/social-providers"),
        }
        parameters = document["paths"]["/admin-api/system/auth/login"]["post"]["parameters"]
        assert any(
            item["name"] == "X-Tenant-Id" and item["in"] == "header" and item["required"]
            for item in parameters
        )
        callback = document["paths"]["/admin-api/system/sms/callback"]["post"]
        assert {item["name"] for item in callback["parameters"]} == {"token"}


async def test_anonymous_context_isolated_until_background_completes(
    system_app, admin_client, probes
):
    tenant_b = await create_tenant(admin_client)
    probes["frames"].clear()
    probes["background"].clear()
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        pending = asyncio.create_task(
            client.get("/test/tenant/lifecycle?wait=yes", headers={"X-Tenant-Id": "1"})
        )
        await asyncio.wait_for(probes["entered"].wait(), 10)
        first = probes["frames"][-1]
        second = await client.get("/test/tenant/lifecycle", headers={"X-Tenant-Id": tenant_b})
        assert second.json() == {"tenant": tenant_b}
        assert first.active and first.tenant_id == "1"
        assert not probes["frames"][-1].active
        probes["release"].set()
        assert (await pending).json() == {"tenant": "1"}
    assert [frame.tenant_id for frame in probes["background"]] == [tenant_b, "1"]
    assert all(not frame.active for frame in probes["frames"])
    with system_app.state.application_context.execution():
        context = system_app.state.application_context.container.get(TenantContext)
        with pytest.raises(TenantException):
            context.current()


async def test_anonymous_context_released_on_error_and_cancellation(system_app, probes):
    probes["entered"].clear()
    probes["release"].clear()
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        failed = await client.get("/test/tenant/lifecycle?fail=yes", headers={"X-Tenant-Id": "1"})
        assert failed.json()["code"] == SecurityErrorCodes.DENIED.code
        assert not probes["frames"][-1].active
        pending = asyncio.create_task(
            client.get("/test/tenant/lifecycle?wait=yes", headers={"X-Tenant-Id": "1"})
        )
        await asyncio.wait_for(probes["entered"].wait(), 10)
        frame = probes["frames"][-1]
        assert frame.active
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert not frame.active


async def test_social_completion_restores_tenant_from_server_binding(
    system_app, admin_client, monkeypatch
):
    tenant_b = await create_tenant(admin_client)
    binding = uuid4().hex + uuid4().hex
    application = system_app.state.application_context
    with application.execution():
        await application.container.get(CacheHandler).set(
            SystemCacheKeyConstants.SOCIAL_LOGIN_TENANT,
            hashlib.sha256(binding.encode()).hexdigest(),
            tenant_b,
        )
    observed = []

    async def reached(self, req):
        observed.append(self.tenant.get_required_tenant_id())
        raise SecurityException(SecurityErrorCodes.CREDENTIALS)

    monkeypatch.setattr(AuthAdminAuthServiceImpl, "social_login", reached)
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        client.cookies.set("system_social_binding", binding)
        body = {"type": SocialTypeEnum.ALIPAY.code, "code": "vendor-code", "state": "a" * 64}
        denied = (
            await client.post(
                "/admin-api/system/auth/social-login", json=body, headers={"X-Tenant-Id": "1"}
            )
        ).json()
        assert denied["code"] == SecurityErrorCodes.DENIED.code
        assert observed == []
        result = (await client.post("/admin-api/system/auth/social-login", json=body)).json()
        assert result["code"] == SecurityErrorCodes.CREDENTIALS.code, result
        assert observed == [tenant_b]
