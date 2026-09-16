import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from starter_security.test_context_and_adapters import MessageProofs
from starter_security.test_workload import WorkloadProofs

from framework.starter_data_permission.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.workload_identity import WorkloadIdentity
from server.starter_server import create_app


class Exemptions:
    async def authorize(self, identity, resource, operation, reason):
        return reason == "approved-maintenance" and identity.tenant_id == "t1"


async def test_snapshot_is_fixed_expiry_and_revocation(permission_case):
    case = permission_case
    token, identity = case.issue()
    async with case.enter(token):
        frame = case.service.current()
        assert await case.ids() == [1]
        await case.set_rules(DataScope.ALL)
        assert await case.ids() == [1]
        assert case.service.current() is frame
        case.context.invalidate(identity.family_id)
        with pytest.raises(DataPermissionException):
            await case.ids()
    case.tokens.sessions[identity.token_digest] = identity.model_copy(update={"revoked": True})
    with pytest.raises(SecurityException):
        async with case.enter(token):
            pass
    case.tokens.sessions[identity.token_digest] = identity.model_copy(
        update={"authorization_revision": case.revisions[("t1", "m1")]}
    )
    case.service.settings = case.service.settings.model_copy(update={"snapshot_seconds": 0.02})
    async with case.enter(token):
        await asyncio.sleep(0.04)
        with pytest.raises(DataPermissionException) as error:
            await case.ids()
        assert error.value.reason == "stale"


async def test_parallel_subjects_applications_and_stale_tasks(permission_case, config_dir):
    case = permission_case
    await case.set_rules(DataScope.SELF, member="m2")
    await case.set_rules(DataScope.SELF, tenant="t2")
    credentials = [case.issue()[0], case.issue(member="m2")[0], case.issue(tenant="t2")[0]]

    async def read(token):
        async with case.enter(token):
            await asyncio.sleep(0)
            return await case.ids()

    assert await asyncio.gather(*(read(token) for token in credentials)) == [[1], [2], [5]]
    other = create_app(base_dir=config_dir({"banner": {"enabled": False}}), environ={})
    async with other.router.lifespan_context(other):
        async with case.enter():
            with other.state.application_context.execution():
                with pytest.raises(DataPermissionException):
                    await case.ids()

    release = asyncio.Event()

    async def inherited():
        await release.wait()
        with pytest.raises(DataPermissionException):
            await case.ids()

    async with case.enter():
        child = asyncio.create_task(inherited())
    release.set()
    await child


async def test_exception_cancel_and_close_drain(permission_case):
    case = permission_case
    with pytest.raises(RuntimeError, match="business"):
        async with case.enter():
            raise RuntimeError("business")
    assert case.service._active == case.tenant.active == 0
    started = asyncio.Event()

    async def work():
        async with case.enter():
            started.set()
            await asyncio.Future()

    task = asyncio.create_task(work())
    await started.wait()
    closing = asyncio.create_task(case.service.close())
    await asyncio.sleep(0)
    assert not closing.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await closing
    assert case.service._active == case.tenant.active == 0


async def test_cancel_permission_loading_cleans_tenant(permission_case):
    case = permission_case
    case.provider.wait = asyncio.Event()
    task = asyncio.create_task(case.security.run(case.issue()[0], case.route, case.ids))
    for _ in range(100):
        if case.provider.calls["rules"]:
            break
        await asyncio.sleep(0.002)
    assert case.provider.calls["rules"] == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert case.service._active == case.tenant.active == 0


async def test_exemption_scope_nested_and_identity_map(permission_case):
    case = permission_case
    async with case.enter():
        with pytest.raises(DataPermissionException):
            async with case.service.exempt(case.Item.__table__.key, "select", reason="unapproved"):
                pass
        case.service.exemptions = Exemptions()
        resource = case.Item.__table__.key
        async with case.service.exempt(resource, "select", reason="approved-maintenance"):
            assert await case.ids() == [1, 2, 3, 4]
            with pytest.raises(RuntimeError):
                async with case.service.exempt(resource, "update", reason="approved-maintenance"):
                    assert case.service.is_exempt(resource, "update")
                    raise RuntimeError()
            assert not case.service.is_exempt(resource, "update")
            assert case.service.is_exempt(resource, "select")
        assert await case.ids() == [1]
        async with case.database.read_session() as session:
            assert (await session.get(case.Item, 1)).id == 1
            async with case.service.exempt(resource, "select", reason="approved-maintenance"):
                with pytest.raises(DataPermissionException):
                    await session.get(case.Item, 1)


async def test_message_reauth_does_not_trust_claims_and_cleans(permission_case):
    case = permission_case
    messages = MessageProofs()
    messages.tokens = case.tokens
    case.security._messages = messages
    token, identity = case.issue()
    payload = b'{"tenant_id":"t2","tenant_all":true}'
    async with case.enter(token):
        proof = await case.security.issue_message(payload, audience="dp-test")
    await case.set_rules(DataScope.SELF)

    async def consume(body):
        assert body == payload
        return await case.ids()

    assert await case.security.run_message(
        proof, payload, case.route, consume, audience="dp-test"
    ) == [1]
    assert case.service._active == case.tenant.active == 0
    with pytest.raises(SecurityException):
        await case.security.run_message(proof, payload, case.route, consume, audience="dp-test")
    with pytest.raises(DataPermissionException):
        case.service.current()


async def test_workload_is_denied_until_explicit_scoped_exemption(permission_case):
    case = permission_case
    messages = WorkloadProofs()
    case.security._messages = messages
    identity = WorkloadIdentity(
        application_id=case.security.settings.application_id,
        domain="admin",
        service_id="job",
        tenant_id="t1",
        audience="dp-test",
        capabilities=frozenset({"dp:read"}),
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    case.service.exemptions = Exemptions()

    async def consume(payload):
        assert await case.ids() == []
        async with case.service.exempt(
            case.Item.__table__.key, "select", reason="approved-maintenance"
        ):
            assert await case.ids() == [1, 2, 3, 4]
        assert await case.ids() == []

    proof = messages.add(identity, capability="dp:read")
    await case.security.run_workload_message(
        proof, b"body", consume, audience="dp-test", capability="dp:read"
    )
    assert case.service._active == case.tenant.active == 0


async def test_permission_change_during_loading_rejects_mixed_snapshot(permission_case):
    case = permission_case
    case.provider.wait = asyncio.Event()
    token, _ = case.issue()
    task = asyncio.create_task(case.security.run(token, case.route, case.ids))
    for _ in range(100):
        if case.provider.calls["rules"]:
            break
        await asyncio.sleep(0.002)
    assert case.provider.calls["rules"] == 1
    await case.set_rules(DataScope.ALL)
    case.provider.wait.set()
    with pytest.raises(DataPermissionException) as error:
        await task
    assert error.value.reason == "stale"
    assert case.service._active == case.tenant.active == 0
