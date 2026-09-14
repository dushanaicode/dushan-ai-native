import asyncio
import threading

import pytest

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_security.core.password_encoder import PasswordEncoder
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.routing.route_policy import RoutePolicy


async def test_cancel_authentication_cleans_execution(security_factory, monkeypatch):
    async with security_factory() as case:
        token, _ = await case.issue()
        entered = asyncio.Event()

        async def blocked(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(case.service.tokens, "resolve", blocked)
        task = asyncio.create_task(case.get(token))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert case.service.resources()["active_operations"] == 0
        assert case.service.context.current() is None
        assert case.application.tasks.active_count == 0


async def test_service_close_drains_and_waiter_cancel_does_not_close_early(security_factory):
    async with security_factory() as case:
        token, _ = await case.issue()
        entered, release = asyncio.Event(), asyncio.Event()

        async def body():
            entered.set()
            await release.wait()
            assert case.service.context.require().account_id == "account-1"

        running = asyncio.create_task(case.service.run(token, RoutePolicy(), body))
        await entered.wait()
        closing = asyncio.create_task(case.service.close())
        await asyncio.sleep(0)
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert case.service.resources() == {"state": "closing", "active_operations": 1}
        with pytest.raises(SecurityException, match="不可用"):
            await case.service.run(token, RoutePolicy(), body)
        release.set()
        await running
        await case.service.close()
        await case.service.close()
        assert case.service.resources() == {"state": "closed", "active_operations": 0}


async def test_password_cancellation_waits_for_worker_and_close(security_factory, monkeypatch):
    async with security_factory() as case:
        with case.application.execution():
            encoder = case.application.get_bean(PasswordEncoder)
            entered, release = threading.Event(), threading.Event()

            def worker(password):
                entered.set()
                assert release.wait(5)
                return b"hash"

            monkeypatch.setattr(encoder, "_hash", worker)
            task = asyncio.create_task(encoder.hash("password"))
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(0.01)
            assert entered.is_set()
            task.cancel()
            closing = asyncio.create_task(encoder.close())
            await asyncio.sleep(0.02)
            assert not closing.done() and not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            await closing
            with pytest.raises(SecurityException):
                await encoder.hash("new")


async def test_cache_probe_startup_failure_rolls_back(security_factory, monkeypatch):
    original = CacheHandler.eval_atomic

    async def fail_probe(self, key, *args, **kwargs):
        if key.key == "security:permissions":
            raise RuntimeError("security probe failed")
        return await original(self, key, *args, **kwargs)

    monkeypatch.setattr(CacheHandler, "eval_atomic", fail_probe)
    with pytest.raises(Exception):
        async with security_factory(cache=True):
            pytest.fail("Security 探活失败不能就绪")
