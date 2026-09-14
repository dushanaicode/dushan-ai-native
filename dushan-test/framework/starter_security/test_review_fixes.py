import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Annotated

import pytest
from fastapi import APIRouter, Body, File, UploadFile
from pydantic import BaseModel, ValidationError

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_di.context.get_bean import get_bean
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.bizlog.diff_field import DiffField
from framework.starter_security.bizlog.log_record import log_record
from framework.starter_security.bizlog.log_record_spec import LogRecordSpec
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_web.routing.route_policy import RoutePolicy

from .test_context_and_adapters import TenantContract
from .test_workload import WorkloadProofs, WorkloadTenant


def session_values(**changes):
    return (
        dict(
            application_id="app",
            domain="admin",
            token_digest="0" * 64,
            session_id="s",
            family_id="f",
            account_id="a",
            realm=SecurityRealm.TENANT,
            tenant_id="tenant-1",
            access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
            membership_id="m1",
            authority_tenant_id="tenant-1",
            authority_membership_id="m1",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision="1",
            scopes=frozenset(),
        )
        | changes
    )


@pytest.mark.parametrize(
    "changes",
    [
        {
            "access_mode": None,
            "membership_id": None,
            "authority_tenant_id": None,
            "authority_membership_id": None,
        },
        {"authority_tenant_id": None},
        {"membership_id": None, "dept_id": "dept"},
        {"authority_tenant_id": "foreign"},
        {"group_id": "group"},
        {
            "access_mode": TenantAccessMode.GROUP_MANAGED,
            "membership_id": None,
            "authority_tenant_id": "hq",
        },
        {
            "access_mode": TenantAccessMode.GROUP_MANAGED,
            "group_id": "g",
            "management_relation_id": "r",
        },
    ],
)
def test_reject_inconsistent_tenant_identity_shapes(changes):
    with pytest.raises(ValidationError):
        LoginSession(**session_values(**changes))


@pytest.mark.parametrize(
    "declaration",
    [
        {"realm": SecurityRealm.SUPPORT},
        {
            "realm": SecurityRealm.SUPPORT,
            "required_capability": "support_session",
            "required_entitlement": "support_session",
            "required_support_resource": "tenant_overview",
            "required_support_action": "write",
        },
        {
            "realm": SecurityRealm.PLATFORM,
            "allowed_tenant_access_modes": frozenset({TenantAccessMode.DIRECT_MEMBERSHIP}),
        },
        {"realm": SecurityRealm.TENANT, "allowed_tenant_access_modes": frozenset()},
    ],
)
def test_invalid_tenant_route_contract_rejected(declaration):
    with pytest.raises(ValueError):
        RoutePolicy(**declaration)


async def test_access_modes_entitlements_and_support_resource_are_enforced(security_factory):
    tenant = TenantContract()
    policy = RoutePolicy(
        ("read",),
        realm=SecurityRealm.TENANT,
        required_capability="group_managed_access",
        required_entitlement="group_managed_access",
    )
    async with security_factory(tenant=tenant, policy=policy) as case:
        direct, _ = await case.issue(
            realm=SecurityRealm.TENANT,
            tenant_id="tenant-1",
            effective_capabilities=frozenset({"group_managed_access"}),
        )
        no_entitlement, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")
        managed, _ = await case.issue(
            realm=SecurityRealm.TENANT,
            tenant_id="tenant-1",
            access_mode=TenantAccessMode.GROUP_MANAGED,
            membership_id=None,
            authority_tenant_id="hq",
            authority_membership_id="hq-member",
            group_id="g",
            management_relation_id="r",
            effective_capabilities=frozenset({"group_managed_access"}),
        )
        assert (await case.get(direct)).json()["tenant"] == "tenant-1"
        assert (await case.get(no_entitlement)).json()["code"] == 403
        assert (await case.get(managed)).json()["code"] == 403
        with case.application.execution():
            allowed = RoutePolicy(
                ("read",),
                realm=SecurityRealm.TENANT,
                allowed_tenant_access_modes=frozenset({TenantAccessMode.GROUP_MANAGED}),
            )
            async with case.service.authorized(managed, allowed):
                assert case.service.context.require().group_id == "g"
        declaration = case.app.openapi()["paths"]["/protected"]["get"]["x-route-access"]
        assert declaration["allowed_tenant_access_modes"] == ["direct_membership"]
        assert declaration["required_entitlement"] == "group_managed_access"
    support = RoutePolicy(
        ("support:read",),
        realm=SecurityRealm.SUPPORT,
        required_capability="support_session",
        required_entitlement="support_session",
        required_support_resource="tenant_overview",
        required_support_action="read",
    )
    async with security_factory(tenant=tenant, policy=support) as case:
        token, _ = await case.issue(
            realm=SecurityRealm.SUPPORT,
            tenant_id="tenant-1",
            platform_operator_id="p",
            support_session_id="support",
            approved_resource="other",
            approved_action="read",
            effective_capabilities=frozenset({"support_session"}),
            granted=("support:read",),
        )
        assert (await case.get(token)).json()["code"] == 403


@pytest.mark.parametrize(
    "inner",
    [RoutePolicy.public(), RoutePolicy(("read",)), RoutePolicy(("admin",), permission_mode="any")],
)
@pytest.mark.parametrize("nested", [False, True])
async def test_outer_route_policy_cannot_be_replaced(security_factory, inner, nested):
    router = APIRouter()
    RoutePolicy(("admin",))(router)
    child = APIRouter()
    if nested:
        inner(child)
        child.add_api_route("/protected", lambda: {"leak": True})
    else:
        child.add_api_route("/protected", inner(lambda: {"leak": True}))
    router.include_router(child)
    with pytest.raises(Exception) as raised:
        async with security_factory(router=router):
            pytest.fail("声明冲突不能上线")
    assert isinstance(raised.value.__cause__, ValueError)
    assert "外层与内层访问声明冲突" in str(raised.value.__cause__)


async def test_unknown_domain_fails_before_ready(security_factory):
    with pytest.raises(Exception):
        async with security_factory(policy=RoutePolicy(domain="adimn")):
            pytest.fail("未知认证域不能发布")


@pytest.mark.parametrize("kind", ["method", "mro"])
async def test_controller_and_mro_policy_conflicts(config_dir, module_package, kind):
    from server.starter_server import create_app

    source = """
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy

@controller('/base', policy=RoutePolicy(('admin',)))
class Base:
    @route('/item', policy=METHOD_POLICY)
    async def item(self): return {'leak': True}
""".replace("METHOD_POLICY", "RoutePolicy.public()" if kind == "method" else "None")
    if kind == "mro":
        source += "\n@controller('/child', policy=RoutePolicy.public())\nclass Child(Base): pass\n"
    package = "security_controller_" + kind
    module_package(package, files={"controllers.py": source})
    app = create_app(
        base_dir=config_dir(
            {"modules": {"packages": ["framework", package], "enabled": ["framework", package]}}
        ),
        environ={},
        access_provider=lambda: None,
    )
    with pytest.raises(Exception) as raised:
        async with app.router.lifespan_context(app):
            pytest.fail("控制器/MRO 的保护声明不能被削弱")
    assert "访问声明冲突" in str(raised.value.__cause__)
    assert app.state.application_context is None


async def test_provider_business_rejection_preserves_contract(security_factory):
    class DeniedTenant(TenantContract):
        @asynccontextmanager
        async def enter(self, session, policy):
            raise BaseBusinessException(GlobalErrorCodeConstants.FORBIDDEN, msg="租户已停用")
            yield

    async with security_factory(
        tenant=DeniedTenant(), policy=RoutePolicy(realm=SecurityRealm.TENANT)
    ) as case:
        token, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")
        response = await case.get(token)
        assert response.json()["code"] == 403 and response.json()["message"] == "租户已停用"


@pytest.mark.parametrize(
    "invalid",
    [
        {"account_enabled": False},
        {"current_credential_revision": 2},
        {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"revoked": True},
    ],
)
async def test_logout_revokes_even_when_login_admission_fails(security_factory, invalid):
    async with security_factory() as case:
        token, session = await case.issue()
        await case.change(session, **invalid)
        with case.application.execution():
            await case.service.logout(token)
            current = await case.service.tokens.resolve(
                session.token_digest, application_id=session.application_id, domain=session.domain
            )
        assert current.revoked
        await case.change(
            current,
            account_enabled=True,
            current_credential_revision=1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        assert (await case.get(token)).json()["code"] == 401


@pytest.mark.parametrize("eager", [False, True])
def test_tenant_exit_preserves_context_and_runs_with_eager_factory(eager):
    marker = ContextVar("exit_marker", default=None)
    exited = []

    @asynccontextmanager
    async def enter():
        token = marker.set("tenant")
        try:
            yield
        finally:
            await asyncio.sleep(0)
            marker.reset(token)
            exited.append(True)

    async def execute():
        service = SecurityService.__new__(SecurityService)
        service.settings = SimpleNamespace(provider_timeout_seconds=1)
        async with service._tenant_scope(enter()):
            assert marker.get() == "tenant"
        assert marker.get() is None

    loop = asyncio.new_event_loop()
    if eager:
        loop.set_task_factory(asyncio.eager_task_factory)
    try:
        loop.run_until_complete(execute())
    finally:
        loop.close()
    assert exited == [True]


class RegisteredJobs(WorkloadProvider):
    async def authenticate(self, source, *, application_id, domain, capability, tenant_id):
        if source != "log-cleanup" or capability != "logs:cleanup":
            raise SecurityException("denied")
        return WorkloadIdentity(
            application_id=application_id,
            domain=domain,
            service_id="maintenance",
            audience=source,
            tenant_id=tenant_id,
            capabilities=frozenset({capability}),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )


async def test_local_job_authentication_global_scope_and_private_install(security_factory):
    tenant = WorkloadTenant()
    async with security_factory(tenant=tenant, workloads=RegisteredJobs()) as case:
        assert not hasattr(case.service.context, "install_workload")
        assert not hasattr(case.service.context, "install")
        assert not hasattr(case.service.context, "scope")

        async def run():
            identity = case.service.context.current_workload()
            assert identity.tenant_id is None and tenant.current.get() is None
            assert case.service.context.current() is None
            assert case.service.context.get_current_account_id() is None
            return "done"

        assert (
            await case.service.run_workload("log-cleanup", run, capability="logs:cleanup") == "done"
        )
        token, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")
        with case.application.execution():
            async with case.service.authorized(token, RoutePolicy(realm=SecurityRealm.TENANT)):
                assert tenant.current.get() == "tenant-1"
                assert (
                    await case.service.run_workload("log-cleanup", run, capability="logs:cleanup")
                    == "done"
                )
                assert tenant.current.get() == "tenant-1"
        with pytest.raises(SecurityException):
            await case.service.run_workload("unregistered", run, capability="logs:cleanup")
        assert case.service.context.current_workload() is None and tenant.active == 0


async def test_message_must_match_issued_capability_not_broad_identity(security_factory):
    class AnyTenant(WorkloadTenant):
        @asynccontextmanager
        async def enter_workload(self, identity, capability):
            yield

    messages = WorkloadProofs()
    async with security_factory(tenant=AnyTenant(), messages=messages) as case:
        identity = WorkloadIdentity(
            application_id=case.service.settings.application_id,
            domain="admin",
            service_id="worker",
            tenant_id="tenant-1",
            audience="messages",
            capabilities=frozenset({"dispatch", "purge"}),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        proof = messages.add(identity, capability="dispatch")

        async def forbidden(payload):
            pytest.fail("dispatch 消息不能执行 purge")

        with pytest.raises(SecurityException, match="权限"):
            await case.service.run_workload_message(
                proof, b"body", forbidden, audience="messages", capability="purge"
            )


async def test_roles_and_scopes_have_explicit_any_mode(security_factory):
    policy = RoutePolicy(
        roles=("admin", "reader"), scopes=("email", "profile"), role_mode="any", scope_mode="any"
    )
    async with security_factory(policy=policy) as case:
        good, _ = await case.issue()
        denied, _ = await case.issue(roles=("guest",))
        assert (await case.get(good)).json()["account"] == "account-1"
        assert (await case.get(denied)).json()["code"] == 403


@pytest.mark.parametrize("kind", ["json", "multipart"])
async def test_unauthenticated_body_is_not_consumed(security_factory, kind):
    router = APIRouter()
    if kind == "json":

        async def endpoint(body: dict = Body(...)):
            return body

        media_type = "application/json"
    else:

        async def endpoint(file: UploadFile = File(...)):
            return {"name": file.filename}

        media_type = "multipart/form-data; boundary=attack"
    router.add_api_route("/protected", RoutePolicy(("admin",))(endpoint), methods=["POST"])
    async with security_factory(router=router) as case:
        token, _ = await case.issue()
        consumed = []

        async def content():
            consumed.append(True)
            yield b"malformed body that must not be read"

        for headers, code in (({}, 401), ({"Authorization": "Bearer " + token}, 403)):
            response = await case.client.post(
                "/protected", headers={"Content-Type": media_type, **headers}, content=content()
            )
            assert response.json()["code"] == code
            assert consumed == []


async def test_diff_and_request_projection_reach_persistent_audit(security_factory):
    class Item(BaseModel):
        value: Annotated[str, DiffField("值")]

    router = APIRouter()

    @log_record(LogRecordSpec("item", "update", "{{ diff }}", "42"))
    async def endpoint(identifier: str):
        await get_bean(BizLogService).record_diff(Item(value="old"), Item(value="new"))
        return {"updated": True}

    router.add_api_route("/items/{identifier}", RoutePolicy()(endpoint))
    async with security_factory(router=router, audit=True) as case:
        token, _ = await case.issue()
        response = await case.get(
            token,
            path="/items/private-path?token=private-query",
            headers={
                "User-Agent": "Browser/" + token + " password=private-pass",
                "X-Forwarded-For": "198.51.100.1",
            },
        )
        assert response.json()["updated"]
        with case.application.execution():
            service = case.application.get_bean(BizLogService)
        event = service.provider.events[-1]
        assert "old" in event.action and "new" in event.action
        assert event.operation.request.request_method == "GET"
        assert event.operation.request.request_url == "/items/{identifier}"
        assert event.operation.request.user_ip == "127.0.0.1"
        encoded = str(event.operation.request)
        assert "private" not in encoded and token not in encoded
        assert (
            token not in event.operation.request.user_agent
            and "private-pass" not in event.operation.request.user_agent
        )
