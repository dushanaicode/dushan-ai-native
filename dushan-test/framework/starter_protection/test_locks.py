import asyncio
from time import perf_counter

import pytest

from framework.starter_cache.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum as Outcome,
)
from framework.starter_cache.exception.cache_lock_exception import CacheLockException
from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.lock.lock_rule import LockRule


async def test_mutex_across_four_clients(services, subject):
    clients = [await services() for _ in range(4)]
    rule = LockRule(lease_ms=2000, wait_ms=1500, execution_timeout_ms=1000)
    active = 0
    completed = []

    async def work(index):
        nonlocal active
        async with clients[index % 4].locks.hold("mutex", subject, rule=rule):
            active += 1
            assert active == 1
            await asyncio.sleep(0.004)
            completed.append(index)
            active -= 1

    await asyncio.gather(*(work(i) for i in range(20)))
    assert len(completed) == 20 and active == 0


async def test_wait_timeout_nonreentrant_and_duplicate_close(services, subject):
    service = await services()
    rule = LockRule(lease_ms=1500, wait_ms=80, execution_timeout_ms=1000)
    lease = await service.locks.acquire("wait", subject, rule=rule)
    started = perf_counter()
    assert await service.locks.acquire("wait", subject, rule=rule) is None
    elapsed = perf_counter() - started
    assert 0.06 <= elapsed < 0.5
    results = await asyncio.gather(*(lease.close() for _ in range(5)))
    assert results == [Outcome.RELEASED] * 5
    assert await lease.close() is Outcome.RELEASED
    async with service.locks.hold("wait", subject, rule=rule):
        with pytest.raises(ProtectionException) as caught:
            async with service.locks.hold("wait", subject, rule=rule):
                pytest.fail("锁不能可重入")
        assert caught.value.error_code == Codes.LOCK_BUSY


async def test_expired_old_owner_cannot_release_new_owner(services, subject):
    one, two = await services(), await services()
    rule = LockRule(lease_ms=120, wait_ms=0, execution_timeout_ms=70)
    old = await one.locks.acquire("expired", subject, rule=rule)
    await asyncio.sleep(0.15)
    new = await two.locks.acquire("expired", subject, rule=rule)
    assert new is not None
    assert await old.close() is Outcome.LOST_OWNER
    assert await one.locks.acquire("expired", subject, rule=rule) is None
    assert await new.close() is Outcome.RELEASED
    missing = await one.locks.acquire("expired", subject, rule=rule)
    await asyncio.sleep(0.15)
    assert await missing.close() is Outcome.MISSING


async def test_wrong_owner_atomic_release(services, subject):
    service = await services()
    lease = await service.locks.acquire("owner", subject)
    client = service.runtime.cache.get_client(service.runtime.key)
    wrong = RedisLeaseLock(client, lease.primitive.key, 1, 0)
    # 显式构造错误持有者状态，命令仍在真实 Redis 上执行。
    wrong._acquired = True
    assert await wrong.release() is Outcome.LOST_OWNER
    assert await client.get(lease.primitive.key) == lease.primitive._owner_token
    assert await lease.close() is Outcome.RELEASED


async def test_lease_object_is_single_use_across_tasks_and_after_release(services, subject):
    service = await services()
    client = service.runtime.cache.get_client(service.runtime.key)
    primitive = RedisLeaseLock(client, service.settings.key_prefix + ":single_use", 1, 0)
    results = await asyncio.gather(primitive.acquire(), primitive.acquire(), return_exceptions=True)
    assert sum(result is True for result in results) == 1
    assert sum(isinstance(result, CacheLockException) for result in results) == 1
    assert await primitive.release() is Outcome.RELEASED
    with pytest.raises(CacheLockException):
        await primitive.acquire()
    assert await client.exists(primitive.key) == 0


@pytest.mark.parametrize("cancel", [False, True])
async def test_business_failure_and_cancel_release_without_rewrite(services, subject, cancel):
    service = await services()
    entered = asyncio.Event()
    original = LookupError("business-original")

    async def business():
        async with service.locks.hold("failure", subject):
            entered.set()
            if not cancel:
                raise original
            await asyncio.Event().wait()

    task = asyncio.create_task(business())
    await entered.wait()
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else LookupError) as caught:
        await task
    if not cancel:
        assert caught.value is original
    async with service.locks.hold("failure", subject):
        pass
    assert service.resources()["leases"] == 0


async def test_execution_timeout_and_no_renewal(services, subject):
    service = await services()
    rule = LockRule(lease_ms=180, wait_ms=0, execution_timeout_ms=70)
    with pytest.raises(TimeoutError):
        async with service.locks.hold("timeout", subject, rule=rule):
            await asyncio.sleep(0.5)
    assert service.resources()["leases"] == 0
    assert not any("renew" in task.get_name() for task in asyncio.all_tasks())


async def test_key_is_resource_not_lease_configuration(services, subject):
    one, two = await services(), await services()
    lease = await one.locks.acquire("resource", subject, {"id": 5})
    other_rule = LockRule(lease_ms=300, wait_ms=0, execution_timeout_ms=100)
    assert await two.locks.acquire("resource", subject, {"id": 5}, rule=other_rule) is None
    second = await two.locks.acquire("resource", subject, {"id": 6}, rule=other_rule)
    assert second is not None
    await lease.close()
    await second.close()
