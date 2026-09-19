import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage
from framework.starter_web.routing.route_policy import RoutePolicy

from .test_context_and_adapters import MessageProofs, TenantContract


class WorkloadTenant(TenantContract):
    @asynccontextmanager
    async def enter_workload(self, identity, capability):
        if identity.tenant_id != "tenant-1" or capability != "notification:dispatch":
            raise SecurityException(SecurityErrorCodes.DENIED)
        token = self.current.set(identity.tenant_id)
        self.active += 1
        try:
            yield
        finally:
            self.current.reset(token)
            self.active -= 1


class WorkloadProofs(MessageProofs):
    """只验证 SPI，不代表完成 Job 凭据或 broker 的密码学认证。"""

    def __init__(self):
        super().__init__()
        self.workloads = {}

    def add(self, identity, payload=b"body", *, capability="notification:dispatch"):
        proof = secrets.token_bytes(32)
        self.workloads[proof] = (identity, payload, capability)
        return proof

    async def verify_workload(self, proof, payload, **kwargs):
        if proof not in self.workloads or self.workloads[proof][1] != payload:
            raise SecurityException(SecurityErrorCodes.INVALID)
        identity, _, capability = self.workloads.pop(proof)
        return WorkloadMessage(identity=identity, capability=capability)

    async def issue_workload(self, identity, payload, *, audience, capability):
        return self.add(
            identity.model_copy(update={"audience": audience}),
            payload,
            capability=capability,
        )


async def test_system_workload_is_authenticated_narrow_and_not_a_login_identity(security_factory):
    messages, tenant = WorkloadProofs(), WorkloadTenant()
    async with security_factory(tenant=tenant, messages=messages) as case:
        identity = WorkloadIdentity(
            application_id=case.service.settings.application_id,
            domain="admin",
            service_id="outbox-job",
            tenant_id="tenant-1",
            audience="notifications",
            capabilities=frozenset({"notification:dispatch"}),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        proof = messages.add(identity)

        async def consume(payload):
            assert payload == b"body"
            assert case.service.context.current() is None
            assert case.service.context.get_current_account_id() is None
            assert case.service.context.current_workload().service_id == "outbox-job"
            assert tenant.current.get() == "tenant-1"
            with pytest.raises(SecurityException):
                await case.service.has_permissions("*:*:*")
            with pytest.raises(SecurityException):
                await case.service.issue_workload_message(
                    b"body", audience="notifications", capability="admin:all"
                )
            return await case.service.issue_workload_message(
                b"body", audience="notifications", capability="notification:dispatch"
            )

        with pytest.raises(SecurityException):
            await case.service.run_workload_message(
                proof,
                b"tampered",
                consume,
                audience="notifications",
                capability="notification:dispatch",
            )
        next_proof = await case.service.run_workload_message(
            proof, b"body", consume, audience="notifications", capability="notification:dispatch"
        )
        assert next_proof != proof and case.service.context.current_workload() is None
        with pytest.raises(SecurityException):
            await case.service.run_workload_message(
                proof,
                b"body",
                consume,
                audience="notifications",
                capability="notification:dispatch",
            )
        assert tenant.active == 0
        token, _ = await case.issue()
        with case.application.execution():
            async with case.service.authorized(token, RoutePolicy()):
                with pytest.raises(SecurityException):
                    await case.service.issue_workload_message(
                        b"body", audience="notifications", capability="notification:dispatch"
                    )


@pytest.mark.parametrize(
    "changed",
    [
        {"application_id": "other"},
        {"domain": "other"},
        {"audience": "other"},
        {"tenant_id": "other"},
        {"capabilities": frozenset()},
        {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
    ],
)
async def test_workload_wrong_binding_and_expiry_are_rejected(security_factory, changed):
    messages, tenant = WorkloadProofs(), WorkloadTenant()
    async with security_factory(tenant=tenant, messages=messages) as case:
        identity = WorkloadIdentity(
            application_id=case.service.settings.application_id,
            domain="admin",
            service_id="outbox-job",
            tenant_id="tenant-1",
            audience="notifications",
            capabilities=frozenset({"notification:dispatch"}),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        ).model_copy(update=changed)

        async def forbidden(payload):
            pytest.fail("未验证或越权的工作负载不能进入业务")

        with pytest.raises(SecurityException):
            await case.service.run_workload_message(
                messages.add(identity),
                b"body",
                forbidden,
                audience="notifications",
                capability="notification:dispatch",
            )
        assert case.service.context.current_workload() is None and tenant.active == 0
