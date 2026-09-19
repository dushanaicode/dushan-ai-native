import asyncio
import secrets
from contextlib import asynccontextmanager
from contextvars import ContextVar

import pytest
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_web.routing.route_policy import RoutePolicy


class TenantContract(TenantAccessProvider):
    """仅验证 Tenant 接点；不声称实现数据库租户隔离。"""

    def __init__(self):
        self.current = ContextVar("test_tenant", default=None)
        self.active = 0

    def supports(self, capability):
        return capability in {
            "support_session",
            "group_managed_access",
            "group_data_sharing",
            "platform_control_plane",
        }

    @asynccontextmanager
    async def enter(self, session, policy):
        if session.tenant_id != "tenant-1":
            raise SecurityException(SecurityErrorCodes.DENIED)
        if session.realm is SecurityRealm.SUPPORT and policy.permissions != ("support:read",):
            raise SecurityException(SecurityErrorCodes.DENIED)
        token = self.current.set(session.tenant_id)
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1
            self.current.reset(token)


class MessageProofs(MessageSecurityProvider):
    """测试的一次性随机证明存储；不是生产 broker 认证或签名实现。"""

    def __init__(self):
        self.proofs = {}
        self.tokens = None

    async def issue(self, session, payload, *, audience):
        proof = secrets.token_bytes(32)
        self.proofs[proof] = (
            session.application_id,
            session.domain,
            audience,
            session.token_digest,
            payload,
        )
        return proof

    async def verify(self, proof, payload, *, application_id, domain, audience):
        value = self.proofs.get(proof)
        if value is None or value[:3] != (application_id, domain, audience) or value[4] != payload:
            raise SecurityException(SecurityErrorCodes.INVALID)
        del self.proofs[proof]
        return await self.tokens.resolve(value[3], application_id=application_id, domain=domain)


async def test_concurrent_requests_and_independent_di_tasks(security_factory):
    async with security_factory() as case:
        credentials = [await case.issue(account_id=f"account-{index}") for index in range(16)]
        responses = await asyncio.gather(*(case.get(token) for token, _ in credentials))
        assert [r.json()["account"] for r in responses] == [
            f"account-{index}" for index in range(16)
        ]
        assert case.service.context.current() is None
        token, _ = credentials[0]

        async def plain_task():
            return case.service.context.current()

        async def secured():
            assert case.service.context.require().account_id == "account-0"
            assert await case.application.tasks.run(plain_task) is None
            assert await case.application.tasks.create_task(plain_task) is None

        await case.service.run(token, RoutePolicy(), secured)
        assert case.service.context.current() is None


async def test_inherited_context_expires_with_parent_scope(security_factory):
    async with security_factory() as case:
        token, _ = await case.issue()
        release = asyncio.Event()

        async def late_child():
            await release.wait()
            return case.service.context.current()

        with case.application.execution():
            async with case.service.authorized(token, RoutePolicy()):
                task = asyncio.create_task(late_child())
            release.set()
            assert await task is None


async def test_multi_application_and_domain_boundaries(security_factory):
    async with (
        security_factory() as first,
        security_factory(
            domains=("admin", "member"), policy=RoutePolicy(domain="member")
        ) as second,
    ):
        first_token, _ = await first.issue()
        second_token, _ = await second.issue(domain="member", account_id="member-1")
        assert (
            first.service is not second.service
            and first.service.tokens is not second.service.tokens
        )
        assert (await second.get(first_token)).json()["code"] == SecurityErrorCodes.INVALID.code
        assert (await second.get(second_token)).json()["account"] == "member-1"
        wrong_domain, _ = await second.issue(domain="admin")
        assert (await second.get(wrong_domain)).json()["code"] == SecurityErrorCodes.INVALID.code
        with first.application.execution():
            async with first.service.authorized(first_token, RoutePolicy()):
                with second.application.execution():
                    assert first.service.context.current() is None


async def test_tenant_source_and_missing_adapter(security_factory):
    policy = RoutePolicy(("read",), tenant_required=True, realm=SecurityRealm.TENANT)
    with pytest.raises(Exception):
        async with security_factory(policy=policy):
            pytest.fail("缺少 Tenant 适配的明确 Tenant 路由不能发布")
    tenant = TenantContract()
    async with security_factory(policy=policy, tenant=tenant) as case:
        valid, _ = await case.issue(
            realm=SecurityRealm.TENANT, tenant_id="tenant-1", membership_id="m-1"
        )
        foreign, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-2")
        platform, _ = await case.issue(
            realm=SecurityRealm.PLATFORM, platform_operator_id="p-1", granted=("*:*:*",)
        )
        assert (await case.get(valid, headers={"tenant_id": "tenant-2"})).json()[
            "tenant"
        ] == "tenant-1"
        assert (await case.get(foreign)).json()["code"] == SecurityErrorCodes.DENIED.code
        assert (await case.get(platform)).json()["code"] == SecurityErrorCodes.DENIED.code
        assert tenant.active == 0 and tenant.current.get() is None


async def test_messages_validate_proof_audience_replay_and_live_session(security_factory):
    tenant, messages = TenantContract(), MessageProofs()
    policy = RoutePolicy(("read",), realm=SecurityRealm.TENANT)
    async with security_factory(tenant=tenant, messages=messages) as case:
        messages.tokens = case.service.tokens
        token, session = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")

        async def publish():
            return await case.service.issue_message(b"body", audience="billing")

        async def consume(payload):
            assert payload == b"body"
            assert tenant.current.get() == "tenant-1"
            return case.service.context.require().account_id

        proof = await case.service.run(token, policy, publish)
        with pytest.raises(SecurityException):
            await case.service.run_message(proof, b"tampered", policy, consume, audience="billing")
        with pytest.raises(SecurityException):
            await case.service.run_message(proof, b"body", policy, consume, audience="other")
        assert (
            await case.service.run_message(proof, b"body", policy, consume, audience="billing")
            == "account-1"
        )
        for forged in (proof, b'{"user_id":"root","tenant_id":"tenant-1"}', {"account_id": "root"}):
            with pytest.raises(SecurityException):
                await case.service.run_message(forged, b"body", policy, consume, audience="billing")
        pending = await case.service.run(token, policy, publish)
        await case.change(session, revoked=True)
        with pytest.raises(SecurityException, match="撤销"):
            await case.service.run_message(pending, b"body", policy, consume, audience="billing")
        assert case.service.context.current() is None and tenant.active == 0


async def test_support_session_is_scoped_and_cannot_publish(security_factory):
    tenant = TenantContract()
    declarations = dict(
        realm=SecurityRealm.SUPPORT,
        required_capability="support_session",
        required_entitlement="support_session",
        required_support_resource="tenant_overview",
        required_support_action="read",
    )
    policy = RoutePolicy(("support:read",), **declarations)
    async with security_factory(tenant=tenant, messages=MessageProofs(), policy=policy) as case:
        token, _ = await case.issue(
            realm=SecurityRealm.SUPPORT,
            tenant_id="tenant-1",
            platform_operator_id="p-1",
            support_session_id="support-1",
            approved_resource="tenant_overview",
            approved_action="read",
            effective_capabilities=frozenset({"support_session"}),
            granted=("support:read", "write"),
        )
        assert (await case.get(token)).json()["tenant"] == "tenant-1"
        with case.application.execution():
            async with case.service.authorized(token, policy):
                with pytest.raises(SecurityException, match="权限"):
                    await case.service.issue_message(b"body", audience="billing")
            with pytest.raises(SecurityException):
                async with case.service.authorized(token, RoutePolicy(("write",), **declarations)):
                    pytest.fail("支持会话不能绕过审批接点")


async def test_stream_context_lasts_until_complete_response(security_factory):
    router = APIRouter()
    seen = []

    async def stream():
        async def body():
            try:
                seen.append(case.service.context.require().account_id)
                yield b"ok"
                await asyncio.sleep(0)
                seen.append(case.service.context.require().account_id)
            finally:
                seen.append("closed")

        return StreamingResponse(body(), headers={"Content-Length": "2"})

    router.add_api_route("/protected", RoutePolicy()(stream))
    async with security_factory(router=router) as case:
        token, _ = await case.issue()
        assert (await case.get(token)).content == b"ok"
        assert seen == ["account-1", "account-1", "closed"]
        assert case.service.context.current() is None


async def test_message_handler_exception_and_cancellation_release_tenant(security_factory):
    tenant, messages = TenantContract(), MessageProofs()
    policy = RoutePolicy(("read",), realm=SecurityRealm.TENANT)
    async with security_factory(tenant=tenant, messages=messages) as case:
        messages.tokens = case.service.tokens
        token, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")

        async def publish():
            return await case.service.issue_message(b"body", audience="billing")

        async def failed(payload):
            raise ValueError("business failure")

        proof = await case.service.run(token, policy, publish)
        with pytest.raises(ValueError):
            await case.service.run_message(proof, b"body", policy, failed, audience="billing")
        assert tenant.active == 0 and case.service.context.current() is None
        entered = asyncio.Event()

        async def blocked(payload):
            entered.set()
            await asyncio.Event().wait()

        proof = await case.service.run(token, policy, publish)
        task = asyncio.create_task(
            case.service.run_message(proof, b"body", policy, blocked, audience="billing")
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert tenant.active == 0 and case.service.context.current() is None


async def test_sync_endpoint_receives_only_its_execution_identity(security_factory):
    router = APIRouter()

    def endpoint():
        return {"account": case.service.context.get_current_account_id()}

    router.add_api_route("/protected", RoutePolicy()(endpoint))
    async with security_factory(router=router) as case:
        token, _ = await case.issue(account_id="thread-account")
        assert (await case.get(token)).json() == {"account": "thread-account"}
        assert case.service.context.current() is None


async def test_repeated_cancellation_waits_for_async_tenant_cleanup(security_factory):
    entered, cleanup_started, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    current = ContextVar("async_tenant_context", default=None)

    class AsyncTenant(TenantAccessProvider):
        active = False

        @asynccontextmanager
        async def enter(self, session, policy):
            self.active = True
            context_token = current.set(session.tenant_id)
            try:
                yield
            finally:
                cleanup_started.set()
                await release.wait()
                current.reset(context_token)
                self.active = False

    tenant = AsyncTenant()
    async with security_factory(tenant=tenant) as case:
        token, _ = await case.issue(realm=SecurityRealm.TENANT, tenant_id="tenant-1")

        async def body():
            assert current.get() == "tenant-1"
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(case.service.run(token, RoutePolicy(), body))
        await entered.wait()
        task.cancel()
        await cleanup_started.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and tenant.active
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not tenant.active and case.service.context.current() is None
