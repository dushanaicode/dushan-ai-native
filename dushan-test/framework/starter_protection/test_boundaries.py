import asyncio

import httpx
import pytest
from fastapi import APIRouter, Request

from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule
from framework.starter_protection.lock.lock_rule import LockRule
from framework.starter_protection.ratelimiter.circuit_breaker import CircuitBreaker
from framework.starter_protection.ratelimiter.rate_limit_rule import RateLimitRule
from framework.starter_protection.web.idempotent import idempotent
from framework.starter_protection.web.rate_limit import rate_limit


async def test_expired_reservation_does_not_disturb_newer_member(services, subject):
    service = await services()
    rule = RateLimitRule(algorithm="fixed", capacity=2, window_ms=180)
    first = (await service.rate_limiter.reserve("overlap", subject, rule=rule)).reservation
    await asyncio.sleep(0.10)
    second = (await service.rate_limiter.reserve("overlap", subject, rule=rule)).reservation
    await asyncio.sleep(0.11)
    assert await service.rate_limiter.release(first) == "expired"
    assert await service.rate_limiter.release(second) == "released"


async def test_idempotency_cleanup_failure_preserves_business_exception(
    services, subject, response_gate
):
    service = await services(
        cache_overrides={"port": response_gate.port},
        io_timeout_seconds=0.04,
        idempotency={"failure_action": "release"},
    )
    original = ValueError("no-side-effects")
    try:
        with pytest.raises(ValueError) as caught:
            async with service.idempotency.guard(
                "failure-cleanup", subject, 1, release_on=(ValueError,)
            ):
                response_gate.pause()
                raise original
        assert caught.value is original
        assert isinstance(caught.value.__cause__, BaseExceptionGroup)
        assert any(
            isinstance(error, ProtectionException) for error in caught.value.__cause__.exceptions
        )
    finally:
        response_gate.resume()


async def test_idempotency_success_cleanup_cancellation_is_drained(
    services, subject, response_gate
):
    service = await services(
        cache_overrides={"port": response_gate.port},
        io_timeout_seconds=0.4,
        idempotency={"mode": "delete_on_complete"},
    )

    async def business():
        async with service.idempotency.guard("cancel-cleanup", subject, 1):
            response_gate.pause()

    task = asyncio.create_task(business())
    await asyncio.wait_for(response_gate.blocked.wait(), 1)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    response_gate.resume()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert service.resources()["active_operations"] == 0
    assert (await service.idempotency.acquire("cancel-cleanup", subject, 1)).status == "acquired"


async def test_expired_idempotent_business_cannot_claim_success(services, subject):
    service = await services()
    rule = IdempotencyRule(mode="fixed", ttl_ms=60, max_lifetime_ms=60, failure_action="retain")
    with pytest.raises(ProtectionException) as caught:
        async with service.idempotency.guard("too-long", subject, 1, rule=rule):
            await asyncio.sleep(0.09)
    assert caught.value.error_code == Codes.OWNER_LOST


async def test_business_ignoring_cancellation_outlives_lease_and_loses_owner(services, subject):
    one, two = await services(), await services()
    rule = LockRule(lease_ms=100, wait_ms=0, execution_timeout_ms=40)
    still_running, release = asyncio.Event(), asyncio.Event()

    async def ignoring_timeout():
        async with one.locks.hold("outlive", subject, rule=rule):
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                still_running.set()
                await release.wait()

    task = asyncio.create_task(ignoring_timeout())
    await still_running.wait()
    await asyncio.sleep(0.09)
    new = await two.locks.acquire("outlive", subject)
    assert new is not None and not task.done()
    release.set()
    with pytest.raises(ProtectionException) as caught:
        await task
    assert caught.value.error_code == Codes.LOCK_LOST
    assert await one.locks.acquire("outlive", subject) is None
    await new.close()


async def test_named_cache_client_routes_all_three_states(services, subject):
    service = await services(client_name="second")
    await service.rate_limiter.acquire("named", subject)
    lease = await service.locks.acquire("named", subject)
    await service.idempotency.acquire("named", subject, 1)
    manager = service.runtime.cache._cache_manager
    primary = manager.get_client("default")
    secondary = manager.get_client("second")
    assert [key async for key in primary.scan_iter(match=service.settings.key_prefix + ":*")] == []
    assert (
        len([key async for key in secondary.scan_iter(match=service.settings.key_prefix + ":*")])
        == 3
    )
    await lease.close()


async def test_redis_acl_command_failure_never_uses_allow_policy(services, subject, namespace):
    admin = await services()
    client = admin.runtime.cache.get_client(admin.runtime.key)
    user = namespace + "_user"
    try:
        await client.execute_command(
            "ACL", "SETUSER", user, "on", ">test-only-password", "~*", "+@all"
        )
        service = await services(
            cache_overrides={"username": user, "password": "test-only-password"},
            rate_failure_policy="allow",
        )
        await client.execute_command("ACL", "SETUSER", user, "-eval")
        with pytest.raises(ProtectionException) as caught:
            await service.rate_limiter.acquire("acl", subject)
        assert caught.value.error_code == Codes.UNAVAILABLE
        assert caught.value.context["reason"] in ("configuration", "command")
        assert service.rate_limiter.circuit.open_until == 0
    finally:
        await client.execute_command("ACL", "DELUSER", user)


def test_circuit_generation_rejects_stale_success():
    circuit = CircuitBreaker(1, 0.01)
    old = circuit.permit()
    circuit.failure(old)
    circuit.success(old)
    assert circuit.open_until > 0 and circuit.permit() is None


async def test_parameter_selector_and_multiple_rule_semantics(protection_app):
    router = APIRouter()
    broad = RateLimitRule(algorithm="fixed", capacity=3, window_ms=3000)
    narrow = RateLimitRule(algorithm="sliding", capacity=1, window_ms=3000)

    @router.post("/selected")
    @idempotent("selected", parameters=lambda bound: {"id": bound.arguments["payload"]["id"]})
    async def selected(request: Request, payload: dict):
        return {"id": payload["id"]}

    @router.get("/rules")
    @rate_limit("rules", rules=(broad, narrow))
    async def endpoint(request: Request):
        return {"ok": True}

    app = await protection_app(routers=[router])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.post("/selected", json={"id": 1, "noise": "a"})).json() == {"id": 1}
        assert (await client.post("/selected", json={"id": 1, "noise": "b"})).json()[
            "code"
        ] == Codes.DUPLICATE.code
        assert (await client.get("/rules")).json() == {"ok": True}
        assert (await client.get("/rules")).json()["code"] == Codes.RATE_LIMITED.code
    with app.state.application_context.execution():
        service = app.state.protection
        redis = service.runtime.cache.get_client(service.runtime.key)
        keys = [
            key
            async for key in redis.scan_iter(match=service.settings.key_prefix + ":rate:fixed:*")
        ]
        assert len(keys) == 1 and await redis.get(keys[0]) == "2"
    with pytest.raises(ValueError):
        rate_limit("rules", rules=(broad, broad))
