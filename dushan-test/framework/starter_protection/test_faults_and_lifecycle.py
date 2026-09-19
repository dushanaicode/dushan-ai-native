import asyncio
from time import perf_counter

import pytest
from loguru import logger

from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.lock.lock_rule import LockRule


@pytest.mark.parametrize("policy", ["block", "allow"])
async def test_real_connection_failure_and_circuit_are_explicit(
    services, subject, response_gate, policy
):
    events = []
    service = await services(
        cache_overrides={"port": response_gate.port},
        rate_failure_policy=policy,
        circuit_failure_threshold=1,
        observer=events.append,
    )
    await response_gate.close()
    if policy == "allow":
        first = await service.rate_limiter.reserve("offline", subject)
        second = await service.rate_limiter.acquire("offline", subject)
        assert first.status == second.status == "degraded"
        assert first.reservation is None
    else:
        with pytest.raises(ProtectionException) as first:
            await service.rate_limiter.acquire("offline", subject)
        assert first.value.error_code == Codes.UNAVAILABLE and first.value.__cause__ is not None
        with pytest.raises(ProtectionException) as second:
            await service.rate_limiter.acquire("offline", subject)
        assert second.value.context["reason"] == "circuit_open"
    assert service.rate_limiter.circuit.open_until > 0
    assert events[-1].outcome == ("degraded" if policy == "allow" else "circuit_open")
    for action in (
        lambda: service.idempotency.acquire("fail", subject, 1),
        lambda: service.locks.acquire("fail", subject),
    ):
        with pytest.raises(ProtectionException) as failure:
            await action()
        assert failure.value.error_code == Codes.UNAVAILABLE


async def test_rate_timeout_does_not_replay_count(services, subject, response_gate):
    direct = await services()
    service = await services(cache_overrides={"port": response_gate.port}, io_timeout_seconds=0.05)
    response_gate.pause()
    started = perf_counter()
    with pytest.raises(ProtectionException) as caught:
        await service.rate_limiter.acquire("timeout", subject)
    assert caught.value.context["reason"] == "timeout"
    assert perf_counter() - started < 0.4
    assert response_gate.blocked.is_set()
    response_gate.resume()
    client = direct.runtime.cache.get_client(direct.runtime.key)
    keys = [key async for key in client.scan_iter(match=direct.settings.key_prefix + ":rate:*")]
    assert len(keys) == 1 and await client.get(keys[0]) == "1"


async def test_indeterminate_idempotent_acquire_retains_committed_claim(
    services, subject, response_gate
):
    direct = await services(idempotency={"ttl_ms": 240, "max_lifetime_ms": 240})
    service = await services(
        cache_overrides={"port": response_gate.port},
        io_timeout_seconds=0.04,
        idempotency={"ttl_ms": 240, "max_lifetime_ms": 240},
    )
    response_gate.pause()
    with pytest.raises(ProtectionException):
        await service.idempotency.acquire("unknown", subject, 3)
    assert response_gate.blocked.is_set()
    assert (await direct.idempotency.acquire("unknown", subject, 3)).status == "duplicate"
    response_gate.resume()
    await asyncio.sleep(0.26)
    assert (await direct.idempotency.acquire("unknown", subject, 3)).status == "acquired"


async def test_cancel_after_lock_set_waits_for_reply_and_releases(services, subject, response_gate):
    service = await services(cache_overrides={"port": response_gate.port}, io_timeout_seconds=0.5)
    direct = await services()
    response_gate.pause()
    pending = asyncio.create_task(service.locks.acquire("cancel-set", subject))
    await asyncio.wait_for(response_gate.blocked.wait(), 1)
    pending.cancel()
    await asyncio.sleep(0)
    pending.cancel()
    response_gate.resume()
    with pytest.raises(asyncio.CancelledError):
        await pending
    async with direct.locks.hold("cancel-set", subject):
        pass
    assert service.resources()["active_operations"] == service.resources()["leases"] == 0


async def test_cancel_during_release_drains_single_background_task(
    services, subject, response_gate
):
    service = await services(cache_overrides={"port": response_gate.port}, io_timeout_seconds=0.5)
    lease = await service.locks.acquire("release", subject)
    response_gate.pause()
    closing = asyncio.create_task(lease.close())
    await asyncio.wait_for(response_gate.blocked.wait(), 1)
    closing.cancel()
    closing.cancel()
    response_gate.resume()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert await lease.close() is await lease.close()
    assert service.resources()["leases"] == 0


async def test_lock_release_and_acquire_use_configured_io_budget(services, subject, response_gate):
    service = await services(
        cache_overrides={"port": response_gate.port, "socket_timeout_seconds": 2.0},
        io_timeout_seconds=0.04,
    )
    lease = await service.locks.acquire("release-timeout", subject)
    response_gate.pause()
    started = perf_counter()
    with pytest.raises(ProtectionException) as caught:
        await lease.close()
    assert caught.value.context["reason"] == "timeout"
    assert perf_counter() - started < 0.4
    response_gate.resume()
    response_gate.pause()
    started = perf_counter()
    with pytest.raises(ProtectionException):
        await service.locks.acquire(
            "acquire-timeout",
            subject,
            rule=LockRule(lease_ms=150, wait_ms=0, execution_timeout_ms=80),
        )
    assert perf_counter() - started < 0.4
    response_gate.resume()
    await asyncio.sleep(0.18)
    assert service.resources()["leases"] == 0


async def test_service_close_waiter_cancel_and_business_drain(services, subject):
    service = await services()
    entered, release = asyncio.Event(), asyncio.Event()

    async def work():
        async with service.idempotency.guard("drain", subject, 1):
            entered.set()
            await release.wait()

    business = asyncio.create_task(work())
    await entered.wait()
    closing = asyncio.create_task(service.close())
    await asyncio.sleep(0)
    assert not closing.done()
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing
    with pytest.raises(ProtectionException) as rejected:
        await service.rate_limiter.acquire("late", subject)
    assert rejected.value.error_code == Codes.CLOSED
    release.set()
    await business
    await service.close()
    assert service.resources() == {
        "state": "closed",
        "active_operations": 0,
        "leases": 0,
        "closing_tasks": 0,
    }


async def test_capacity_close_timeout_retry_and_unclosed_lease(services, subject):
    service = await services(max_inflight=1, shutdown_timeout_seconds=0.04)
    lease = await service.locks.acquire("capacity", subject)
    with pytest.raises(ProtectionException) as caught:
        await service.rate_limiter.acquire("capacity", subject)
    assert caught.value.error_code == Codes.CAPACITY
    await service.close()
    assert lease._close_task.done()
    other = await services(shutdown_timeout_seconds=0.03)
    with other.runtime.operation():
        with pytest.raises(TimeoutError):
            await other.close()
        assert other.resources()["state"] == "close_failed"
    await other.close()
    assert other.resources()["state"] == "closed"


async def test_observer_failure_and_sensitive_diagnostics(services, subject):
    messages, events = [], []

    def broken(event):
        events.append(event)
        raise ValueError("token=observer-raw-secret")

    sink = logger.add(lambda message: messages.append(str(message)))
    try:
        service = await services(observer=broken)
        assert (
            await service.rate_limiter.acquire(
                "secret-operation", subject, {"password": "payload-raw-secret"}
            )
        ).allowed
        assert events and all("secret" not in repr(event) for event in events)
        assert "observer-raw-secret" not in "".join(messages)
        assert "payload-raw-secret" not in "".join(messages)
    finally:
        logger.remove(sink)


async def test_half_open_single_probe_and_cancellation_recovers(services, subject, response_gate):
    service = await services(
        cache_overrides={"port": response_gate.port},
        io_timeout_seconds=0.05,
        circuit_failure_threshold=1,
        circuit_reset_seconds=0.04,
    )
    response_gate.pause()
    with pytest.raises(ProtectionException):
        await service.rate_limiter.acquire("circuit", subject)
    response_gate.resume()
    await asyncio.sleep(0.06)
    response_gate.pause()
    probe = asyncio.create_task(service.rate_limiter.acquire("circuit", subject))
    await asyncio.wait_for(response_gate.blocked.wait(), 1)
    with pytest.raises(ProtectionException) as rejected:
        await service.rate_limiter.acquire("circuit", subject)
    assert rejected.value.context["reason"] == "circuit_open"
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe
    assert not service.rate_limiter.circuit.probing
    response_gate.resume()
    await asyncio.sleep(0.06)
    assert (await service.rate_limiter.acquire("circuit", subject)).allowed
    assert service.rate_limiter.circuit.open_until == 0
