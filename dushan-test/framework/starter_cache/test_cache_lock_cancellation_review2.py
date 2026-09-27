import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.distributed_lock import DistributedLock


def exception_chain(error):
    yield error
    if isinstance(error, BaseExceptionGroup):
        for child in error.exceptions:
            yield from exception_chain(child)
    if error.__cause__ is not None:
        yield from exception_chain(error.__cause__)


@pytest.mark.parametrize("body_outcome", ["success", "error", "cancel"])
@pytest.mark.parametrize("release_fails", [False, True])
async def test_cache_lock_release_preserves_task_cancellation(body_outcome, release_fails):
    body_entered = asyncio.Event()
    release_entered = asyncio.Event()
    release_gate = asyncio.Event()
    release_finished = False
    primary = None
    release_error = RedisConnectionError("释放失败")

    async def release_command(*args):
        nonlocal release_finished
        release_entered.set()
        await release_gate.wait()
        release_finished = True
        if release_fails:
            raise release_error
        return LockReleaseOutcomeEnum.RELEASED.code

    client = SimpleNamespace(
        set=AsyncMock(return_value=True), eval=AsyncMock(side_effect=release_command)
    )
    lock = DistributedLock()
    lock._cache_manager = SimpleNamespace(get_default_client=lambda: client)

    async def run():
        nonlocal primary
        async with lock.with_lock(
            "review2", lease_seconds=60, wait_seconds=0, critical_section_timeout_seconds=30
        ):
            try:
                if body_outcome == "error":
                    raise RuntimeError("业务失败")
                if body_outcome == "cancel":
                    body_entered.set()
                    await asyncio.Event().wait()
            except BaseException as error:
                primary = error
                raise

    task = asyncio.create_task(run())
    if body_outcome == "cancel":
        await body_entered.wait()
        task.cancel("临界区取消")
    await release_entered.wait()
    task.cancel("释放期间取消")
    await asyncio.sleep(0)
    waiting_for_release = not task.done()
    release_gate.set()
    with pytest.raises(asyncio.CancelledError) as caught:
        await task

    assert waiting_for_release and release_finished
    assert task.cancelled()
    client.eval.assert_awaited_once()
    errors = list(exception_chain(caught.value))
    if primary is not None:
        assert primary in errors
    if body_outcome == "cancel":
        assert caught.value is primary
    if release_fails:
        assert release_error in errors
        assert any(
            isinstance(error, CacheException)
            and error.error_code == CacheErrorCodes.LOCK_RELEASE_FAILED
            for error in errors
        )
