import asyncio

import pytest

from fixtures.cache_fixtures import requires_redis
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.definitions.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.distributed_lock import DistributedLock

pytestmark = requires_redis


def lock_of(app) -> DistributedLock:
    return app.state.application_context.get_bean(DistributedLock)


def client_of(app):
    return app.state.application_context.get_bean(CacheManager).get_default_client()


async def test_acquire_and_release_round_trip(cache_case, cache_prefix):
    _, _, app = cache_case
    lock, client = lock_of(app), client_of(app)
    name = f"{cache_prefix}-basic"

    held = await lock.acquire(name, lease_seconds=5)
    assert held is not None
    assert await client.exists(f"lock:{name}") == 1
    assert await lock.release(held) is LockReleaseOutcomeEnum.RELEASED
    assert await client.exists(f"lock:{name}") == 0


async def test_second_acquire_within_wait_window_returns_none(cache_case, cache_prefix):
    _, _, app = cache_case
    lock = lock_of(app)
    name = f"{cache_prefix}-busy"

    held = await lock.acquire(name, lease_seconds=5)
    try:
        assert await lock.acquire(name, lease_seconds=5, wait_seconds=0.2) is None
    finally:
        await lock.release(held)


async def test_with_lock_reports_contention_instead_of_waiting_forever(cache_case, cache_prefix):
    _, _, app = cache_case
    lock = lock_of(app)
    name = f"{cache_prefix}-ctx"

    held = await lock.acquire(name, lease_seconds=5)
    try:
        with pytest.raises(CacheException):
            async with lock.with_lock(
                name, lease_seconds=5, wait_seconds=0.2, critical_section_timeout_seconds=2
            ):
                pass
    finally:
        await lock.release(held)


async def test_with_lock_enforces_the_critical_section_upper_bound(cache_case, cache_prefix):
    _, _, app = cache_case
    lock, client = lock_of(app), client_of(app)
    name = f"{cache_prefix}-slow"

    with pytest.raises(TimeoutError):
        async with lock.with_lock(name, lease_seconds=3, critical_section_timeout_seconds=0.3):
            await asyncio.sleep(5)
    assert await client.exists(f"lock:{name}") == 0


async def test_with_lock_releases_when_the_body_raises(cache_case, cache_prefix):
    _, _, app = cache_case
    lock, client = lock_of(app), client_of(app)
    name = f"{cache_prefix}-boom"

    with pytest.raises(RuntimeError):
        async with lock.with_lock(name, lease_seconds=5, critical_section_timeout_seconds=2):
            raise RuntimeError("业务失败")
    assert await client.exists(f"lock:{name}") == 0


async def test_with_lock_releases_when_the_caller_is_cancelled(cache_case, cache_prefix):
    _, _, app = cache_case
    lock, client = lock_of(app), client_of(app)
    name = f"{cache_prefix}-cancel"
    entered = asyncio.Event()

    async def hold():
        async with lock.with_lock(name, lease_seconds=10, critical_section_timeout_seconds=8):
            entered.set()
            await asyncio.sleep(30)

    task = asyncio.create_task(hold())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert await client.exists(f"lock:{name}") == 0


async def test_lease_expiry_makes_the_lock_available_again(cache_case, cache_prefix):
    _, _, app = cache_case
    lock, client = lock_of(app), client_of(app)
    name = f"{cache_prefix}-lease"

    held = await lock.acquire(name, lease_seconds=1)
    assert 0 < await client.pttl(f"lock:{name}") <= 1000
    await asyncio.sleep(1.2)

    other = await lock.acquire(name, lease_seconds=2)
    assert other is not None
    try:
        # 租约过期后锁已被别人接管，释放必须如实报告所有权丢失，而不是假装成功。
        assert await lock.release(held) is LockReleaseOutcomeEnum.LOST_OWNER
    finally:
        await lock.release(other)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lease_seconds": 0},
        {"lease_seconds": -1},
        {"wait_seconds": -1},
        {"critical_section_timeout_seconds": 0},
        {"lease_seconds": 1, "critical_section_timeout_seconds": 1},
        {"lease_seconds": float("inf")},
    ],
)
async def test_invalid_lock_timing_is_rejected(cache_case, cache_prefix, kwargs):
    _, _, app = cache_case
    with pytest.raises(CacheException):
        lock_of(app).with_lock(f"{cache_prefix}-invalid", **kwargs)


async def test_lock_instance_cannot_be_acquired_twice(cache_case, cache_prefix):
    _, _, app = cache_case
    lock = lock_of(app)
    held = await lock.acquire(f"{cache_prefix}-single", lease_seconds=5)
    try:
        with pytest.raises(CacheException):
            await held.acquire()
    finally:
        await lock.release(held)
