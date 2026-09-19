import asyncio
from dataclasses import replace

import pytest

from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.ratelimiter.rate_limit_rule import RateLimitRule


@pytest.mark.parametrize("algorithm", ["fixed", "sliding"])
async def test_atomic_capacity_across_independent_clients(services, subject, algorithm):
    clients = [await services() for _ in range(4)]
    rule = RateLimitRule(algorithm=algorithm, capacity=17, window_ms=3000)
    results = await asyncio.gather(
        *(clients[i % 4].rate_limiter.acquire("shared", subject, rule=rule) for i in range(120))
    )
    assert sum(result.status == "acquired" for result in results) == 17
    assert all(0 < result.retry_after_ms <= 3000 for result in results if not result.allowed)
    assert (
        len({id(s.runtime.cache.get_client(s.runtime.key).connection_pool) for s in clients}) == 4
    )


@pytest.mark.parametrize("algorithm", ["fixed", "sliding"])
async def test_window_rejection_does_not_extend_ttl(services, subject, algorithm):
    service = await services()
    rule = RateLimitRule(algorithm=algorithm, capacity=1, window_ms=220)
    assert (await service.rate_limiter.acquire("window", subject, rule=rule)).allowed
    first = await service.rate_limiter.acquire("window", subject, rule=rule)
    await asyncio.sleep(0.07)
    second = await service.rate_limiter.acquire("window", subject, rule=rule)
    assert 0 < second.retry_after_ms < first.retry_after_ms
    await asyncio.sleep(second.retry_after_ms / 1000 + 0.03)
    assert (await service.rate_limiter.acquire("window", subject, rule=rule)).allowed


async def test_sliding_retains_newer_events_across_boundary(services, subject):
    service = await services()
    rule = RateLimitRule(algorithm="sliding", capacity=2, window_ms=260)
    assert (await service.rate_limiter.acquire("boundary", subject, rule=rule)).allowed
    await asyncio.sleep(0.14)
    assert (await service.rate_limiter.acquire("boundary", subject, rule=rule)).allowed
    await asyncio.sleep(0.15)
    assert (await service.rate_limiter.acquire("boundary", subject, rule=rule)).allowed
    assert not (await service.rate_limiter.acquire("boundary", subject, rule=rule)).allowed


async def test_reservation_owner_and_expiry_competition(services, subject):
    one, two = await services(), await services()
    rule = RateLimitRule(algorithm="fixed", capacity=1, window_ms=200)
    results = await asyncio.gather(
        *(one.rate_limiter.reserve("slot", subject, rule=rule) for _ in range(30))
    )
    assert sum(result.allowed for result in results) == 1
    old = next(result.reservation for result in results if result.allowed)
    assert await two.rate_limiter.release(replace(old, owner="wrong-owner")) == "not_owner"
    assert not (await two.rate_limiter.reserve("slot", subject, rule=rule)).allowed
    await asyncio.sleep(0.23)
    new = (await two.rate_limiter.reserve("slot", subject, rule=rule)).reservation
    assert old.owner != new.owner
    assert await one.rate_limiter.release(old) == "not_owner"
    assert not (await one.rate_limiter.reserve("slot", subject, rule=rule)).allowed
    assert await one.rate_limiter.release(new) == "released"
    assert await two.rate_limiter.release(new) == "not_owner"
    assert (await one.rate_limiter.reserve("slot", subject, rule=rule)).allowed


async def test_rate_rule_subject_tenant_operation_and_app_isolation(services, subject, namespace):
    one, two = await services(), await services(key_prefix=namespace + "_other")
    rule = RateLimitRule(algorithm="fixed", capacity=1, window_ms=3000)
    assert (await one.rate_limiter.acquire("a", subject, rule=rule)).allowed
    assert not (await one.rate_limiter.acquire("a", subject, rule=rule)).allowed
    for operation, identity in [
        ("b", subject),
        ("a", subject.model_copy(update={"tenant_id": "two"})),
        ("a", subject.model_copy(update={"identifier": "second"})),
    ]:
        assert (await one.rate_limiter.acquire(operation, identity, rule=rule)).allowed
    assert (await two.rate_limiter.acquire("a", subject, rule=rule)).allowed
    assert (
        await one.rate_limiter.acquire("a", subject, rule=rule.model_copy(update={"capacity": 2}))
    ).allowed


async def test_disabled_has_distinct_decision_and_unchanged_storage(services, subject):
    service = await services(rate_limit_enabled=False)
    client = service.runtime.cache.get_client(service.runtime.key)
    for action in (service.rate_limiter.acquire, service.rate_limiter.reserve):
        result = await action("disabled", subject)
        assert result.status == "disabled" and result.reservation is None
    assert [key async for key in client.scan_iter(match=service.settings.key_prefix + ":*")] == []


async def test_corrupt_state_is_not_silently_allowed(services, subject):
    service = await services(rate_failure_policy="allow")
    rule = service.settings.rate_limit
    digest = service.runtime.identifier("corrupt", subject, ())
    key = service.runtime.cache.build_full_key(
        service.runtime.key, f"rate:fixed:{rule.capacity}:{rule.window_ms}:{digest}"
    )
    await service.runtime.cache.get_client(service.runtime.key).set(key, "sensitive-not-a-counter")
    with pytest.raises(ProtectionException) as caught:
        await service.rate_limiter.acquire("corrupt", subject)
    assert caught.value.error_code == Codes.UNAVAILABLE
    assert caught.value.context["reason"] == "command"
    assert service.rate_limiter.circuit.failures == 0
