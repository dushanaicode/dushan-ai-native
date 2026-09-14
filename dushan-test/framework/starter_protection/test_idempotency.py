import asyncio
from dataclasses import replace

import pytest

from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule


@pytest.mark.parametrize("mode", ["fixed", "sliding", "delete_on_complete"])
async def test_atomic_acquire_and_success_policy(services, subject, mode):
    clients = [await services() for _ in range(4)]
    rule = IdempotencyRule(mode=mode, ttl_ms=3000, max_lifetime_ms=5000, failure_action="retain")
    results = await asyncio.gather(
        *(
            clients[i % 4].idempotency.acquire("payment", subject, {"id": 7}, rule=rule)
            for i in range(100)
        )
    )
    assert sum(result.status == "acquired" for result in results) == 1
    assert all(
        0 < result.retry_after_ms <= 3000 for result in results if result.status == "duplicate"
    )
    claim = next(result.claim for result in results if result.claim is not None)
    expected = "released" if mode == "delete_on_complete" else "retained"
    assert await clients[0].idempotency.complete(claim) == expected
    after = await clients[1].idempotency.acquire("payment", subject, {"id": 7}, rule=rule)
    assert after.status == ("acquired" if mode == "delete_on_complete" else "duplicate")


async def test_owner_cleanup_expiry_and_reacquire_race(services, subject):
    one, two = await services(), await services()
    rule = IdempotencyRule(
        mode="delete_on_complete", ttl_ms=5000, max_lifetime_ms=5000, failure_action="release"
    )
    old = (await one.idempotency.acquire("race", subject, 1, rule=rule)).claim
    assert await one.idempotency.complete(replace(old, owner="wrong-owner")) == "not_owner"
    # 错误 owner 与过期竞争分成两阶段，避免并行构建的调度延迟耗尽准备阶段的租约。
    client = one.runtime.cache.get_client(one.runtime.key)
    key = one.runtime.cache.build_full_key(one.runtime.key, old.identifier)
    await client.pexpire(key, 1)
    async with asyncio.timeout(1):
        while await client.exists(key):
            await asyncio.sleep(0.002)
    new, outcome = await asyncio.gather(
        two.idempotency.acquire("race", subject, 1, rule=rule), one.idempotency.complete(old)
    )
    assert new.status == "acquired"
    assert outcome in ("missing", "not_owner")
    assert await one.idempotency.complete(old) == "not_owner"
    assert (await one.idempotency.acquire("race", subject, 1, rule=rule)).status == "duplicate"
    assert await two.idempotency.complete(new.claim) == "released"
    assert await two.idempotency.complete(new.claim) == "missing"


async def test_sliding_is_capped_at_absolute_lifetime(services, subject):
    service = await services()
    rule = IdempotencyRule(mode="sliding", ttl_ms=120, max_lifetime_ms=300, failure_action="retain")
    first = await service.idempotency.acquire("sliding", subject, 1, rule=rule)
    original = first.claim.owner
    for _ in range(3):
        await asyncio.sleep(0.07)
        repeated = await service.idempotency.acquire("sliding", subject, 1, rule=rule)
        assert repeated.status == "duplicate"
    assert repeated.retry_after_ms < 115
    await asyncio.sleep(0.12)
    fresh = await service.idempotency.acquire("sliding", subject, 1, rule=rule)
    assert fresh.status == "acquired" and fresh.claim.owner != original


@pytest.mark.parametrize("failure_action", ["release", "retain"])
@pytest.mark.parametrize("outcome", ["known", "unknown", "cancel"])
async def test_failure_and_cancellation_contract(services, subject, failure_action, outcome):
    service = await services(
        idempotency={"failure_action": failure_action, "ttl_ms": 140, "max_lifetime_ms": 140}
    )
    entered = asyncio.Event()
    original = (
        ValueError("explicit-no-side-effect")
        if outcome == "known"
        else RuntimeError("unknown-after-commit")
    )

    async def work():
        async with service.idempotency.guard(
            "effect", subject, {"id": 1}, release_on=(ValueError,)
        ):
            entered.set()
            if outcome == "cancel":
                await asyncio.Event().wait()
            raise original

    task = asyncio.create_task(work())
    await entered.wait()
    if outcome == "cancel":
        task.cancel()
    with pytest.raises(asyncio.CancelledError if outcome == "cancel" else type(original)) as caught:
        await task
    if outcome != "cancel":
        assert caught.value is original
    expected = "acquired" if outcome == "known" and failure_action == "release" else "duplicate"
    assert (await service.idempotency.acquire("effect", subject, {"id": 1})).status == expected
    await asyncio.sleep(0.17)
    assert (await service.idempotency.acquire("effect", subject, {"id": 1})).status == "acquired"


async def test_guard_executes_once_and_never_replays_result(services, subject):
    one, two = await services(), await services()
    calls = []

    async def work(service):
        async with service.idempotency.guard("once", subject, (9,)):
            calls.append(1)
            await asyncio.sleep(0.02)
            return {"value": 123}

    results = await asyncio.gather(work(one), work(two), return_exceptions=True)
    assert calls == [1]
    assert sum(value == {"value": 123} for value in results) == 1
    failure = next(value for value in results if isinstance(value, Exception))
    assert isinstance(failure, ProtectionException) and failure.error_code == Codes.DUPLICATE


async def test_subject_operation_payload_and_rule_change_boundaries(services, subject, namespace):
    one, two = await services(), await services(key_prefix=namespace + "_b")
    assert (await one.idempotency.acquire("submit", subject, {"a": 1, "b": 2})).status == "acquired"
    changed_rule = one.settings.idempotency.model_copy(update={"ttl_ms": 1000})
    assert (
        await one.idempotency.acquire("submit", subject, {"b": 2, "a": 1}, rule=changed_rule)
    ).status == "duplicate"
    variants = [
        ("other", subject, {"a": 1, "b": 2}),
        ("submit", subject.model_copy(update={"tenant_id": "two"}), {"a": 1, "b": 2}),
        ("submit", subject, {"a": 1, "b": 3}),
        ("submit", subject.model_copy(update={"membership_id": "member-two"}), {"a": 1, "b": 2}),
    ]
    for operation, identity, payload in variants:
        assert (await one.idempotency.acquire(operation, identity, payload)).status == "acquired"
    assert (await two.idempotency.acquire("submit", subject, {"a": 1, "b": 2})).status == "acquired"


async def test_disabled_and_explicit_unknown_failure(services, subject):
    service = await services(idempotency_enabled=False)
    assert (await service.idempotency.acquire("off", subject, 1)).status == "disabled"
    async with service.idempotency.guard("off", subject, 1) as claim:
        assert claim is None
    enabled = await services()
    claim = (await enabled.idempotency.acquire("unknown", subject, 1)).claim
    assert await enabled.idempotency.fail(claim, known_no_effect=False) == "retained"
    assert (await enabled.idempotency.acquire("unknown", subject, 1)).status == "duplicate"


async def test_sliding_absolute_deadline_wins_over_remaining_physical_ttl(services, subject):
    service = await services()
    rule = IdempotencyRule(
        mode="sliding", ttl_ms=1000, max_lifetime_ms=1000, failure_action="release"
    )
    old = (await service.idempotency.acquire("deadline", subject, 1, rule=rule)).claim
    client = service.runtime.cache.get_client(service.runtime.key)
    key = service.runtime.cache.build_full_key(service.runtime.key, old.identifier)
    await client.hset(key, "deadline", 1)
    new = await service.idempotency.acquire("deadline", subject, 1, rule=rule)
    assert new.status == "acquired" and new.claim.owner != old.owner
    assert await service.idempotency.fail(old, known_no_effect=True) == "not_owner"
