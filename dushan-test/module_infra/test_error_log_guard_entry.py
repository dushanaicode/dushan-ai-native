import asyncio
from contextlib import asynccontextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fixtures.config_factory import ConfigFactory
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_logging.context.log_context import LogContext
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from framework.starter_web.middleware.request_context_middleware import RequestContextMiddleware
from framework.starter_web.middleware.web_exception_middleware import WebExceptionMiddleware
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.web_route import WebRoute
from module_infra.service.logger.api_error_log_service_impl import ApiErrorLogServiceImpl
from module_infra.spi.logger.api_error_log_service_provider_adapter import (
    ApiErrorLogServiceProviderAdapter,
)


@pytest.mark.parametrize(
    ("failure_phase", "expected_code"),
    [("permission", 1004009), ("tenant", 1004009), ("data_permission", 500)],
)
async def test_guard_entry_failure_keeps_verified_log_identity_isolated(
    failure_phase, expected_code
):
    settings = SecuritySettings.model_validate(
        {
            **ConfigFactory.values()["config"]["models"]["security"],
            "enabled": True,
            "permission_cache_enabled": False,
        }
    )
    sessions = {}
    for token, account_id, tenant_id in [("a" * 40, "42", "8"), ("b" * 40, "43", "9")]:
        digest = OpaqueToken.digest(token)
        sessions[digest] = LoginSession(
            application_id=settings.application_id,
            domain=settings.default_domain,
            token_digest=digest,
            session_id=f"session-{account_id}",
            family_id=f"family-{account_id}",
            account_id=account_id,
            realm=SecurityRealm.TENANT,
            tenant_id=tenant_id,
            membership_id=account_id,
            authority_tenant_id=tenant_id,
            authority_membership_id=account_id,
            access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision="1",
            scopes=frozenset(),
        )
    owner = object()
    context = SecurityContext(owner)
    barrier = asyncio.Barrier(2)
    provider_identities = []
    error_rows = []
    write_identities = []
    writer_authority = []
    request_identities = []
    endpoint_calls = []

    async def fail_provider():
        await barrier.wait()
        provider_identities.append((context.require().account_id, LogContext.current().tenant_id))
        raise RuntimeError(f"{failure_phase} provider unavailable")

    async def resolve(digest, **kwargs):
        return sessions[digest]

    async def permissions(session, *, binding):
        if failure_phase == "permission":
            await fail_provider()
        return PermissionSnapshot(
            binding=binding,
            revision=session.authorization_revision,
            permissions=frozenset({"infra:websocket:query"}),
            roles=frozenset(),
        )

    @asynccontextmanager
    async def tenant_scope(*args):
        if failure_phase == "tenant":
            await fail_provider()
        yield

    @asynccontextmanager
    async def data_scope(identity, *, capability=None):
        if failure_phase == "data_permission":
            await fail_provider()
        yield

    security = SecurityService(
        settings,
        SimpleNamespace(resolve=resolve),
        SimpleNamespace(snapshot=permissions),
        None,
        context,
    )
    await security.open(
        tenant=SimpleNamespace(is_ready=True, enter=tenant_scope),
        data_access=SimpleNamespace(enter=data_scope),
    )
    policy = RoutePolicy(
        permissions=("infra:websocket:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    access = SecurityAccess()

    def guard(request):
        return access.guard(
            request, policy=RoutePolicy.public() if request.url.path == "/anonymous" else policy
        )

    @asynccontextmanager
    async def workload_scope(code, tenant_id):
        assert code == "infra.log.write"
        write_identities.append((LogContext.current().account_id, tenant_id))
        yield

    async def run_isolated(writer, *args):
        await writer(*args)

    service = ApiErrorLogServiceImpl()
    service.api_error_log_mapper = SimpleNamespace(insert=AsyncMock(side_effect=error_rows.append))
    service.tenant_settings = SimpleNamespace(default_tenant_id="1")
    service.workloads = SimpleNamespace(scope=workload_scope)
    service.database = SimpleNamespace(scope=nullcontext)
    adapter = ApiErrorLogServiceProviderAdapter()
    adapter.service = service
    adapter.settings = settings
    adapter.tasks = SimpleNamespace(run_isolated=run_isolated)

    async def write(record):
        request = RequestContext.current().connection
        request_identities.append((request.headers.get("x-test-account"), record.account_id))
        writer_authority.append(
            (
                context.current(),
                context.current_workload(),
                request.scope["state"].get(SecurityAccess.VERIFIED),
            )
        )
        await adapter.write(record)

    handler = GlobalExceptionHandler(error_recorder=ErrorLogRecorder(write))
    app = FastAPI()
    app.state.security = security
    app.state.web_logging_owner = "guard-entry-test"
    app.state.web_trusted_proxies = ()
    app.router.route_class = partial(WebRoute, access_guard=guard)
    app.add_middleware(WebExceptionMiddleware, handler=handler, owner="guard-entry-test")
    app.add_middleware(RequestContextMiddleware, access_log_enabled=False)
    handler.register(app)

    @app.get("/protected")
    async def protected():
        endpoint_calls.append(True)
        raise AssertionError("provider failure must prevent endpoint entry")

    @app.get("/anonymous")
    async def anonymous():
        raise RuntimeError("anonymous request failed")

    previous_context = LogContext.current()
    binding = ApplicationContext._current.set(SimpleNamespace(application=owner, active=True))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = await asyncio.gather(
                *(
                    client.get(
                        "/protected",
                        headers={"Authorization": f"Bearer {token}", "X-Test-Account": account_id},
                    )
                    for token, account_id in (("a" * 40, "42"), ("b" * 40, "43"))
                )
            )
            anonymous_response = await client.get("/anonymous")
        assert context.current() is None
    finally:
        ApplicationContext._current.reset(binding)
        await security.close()

    assert [response.json()["code"] for response in responses] == [expected_code] * 2
    assert anonymous_response.json()["code"] == 500
    assert endpoint_calls == []
    assert sorted(provider_identities) == [("42", "8"), ("43", "9")]
    assert len(error_rows) == 3
    assert {(row.user_id, row.user_type) for row in error_rows} == {(42, 2), (43, 2), (None, 0)}
    assert set(write_identities) == {("42", "8"), ("43", "9"), (None, "1")}
    assert writer_authority == [(None, None, None)] * 3
    assert set(request_identities) == {("42", "42"), ("43", "43"), (None, None)}
    assert LogContext.current() == previous_context
