import asyncio
from contextvars import ContextVar
from time import monotonic

import pytest

from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.service.ip_location_service import IpLocationService
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


class ControlledProvider(IpLocationProvider):
    name, online = "sample", True

    def __init__(self, result="地区"):
        self.result = result
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def query(self, ip, remaining_seconds):
        self.calls += 1
        self.entered.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        return self.result


@pytest.fixture
async def make_service(ip_settings):
    services = []

    def create(provider, **overrides):
        settings = ip_settings(
            local_enabled=False, online_enabled=True, online_providers=[provider.name], **overrides
        )
        service = IpLocationService(settings, [provider])
        service.open()
        services.append(service)
        return service

    yield create
    for service in services:
        await service.close()


@pytest.mark.parametrize("result", ["地区", None])
async def test_cold_requests_share_one_query_even_when_result_cache_is_disabled(
    make_service, result
):
    provider = ControlledProvider(result)
    service = make_service(provider, cache_max_size=0, unknown_cache_ttl_seconds=0)
    queries = [asyncio.create_task(service.lookup("1.2.3.4")) for _ in range(50)]
    await provider.entered.wait()
    assert provider.calls == 1
    assert service._inflight["1.2.3.4"].waiters == 50
    provider.release.set()
    results = await asyncio.gather(*queries)
    assert all(value is results[0] for value in results)
    assert results[0].status == ("found" if result is not None else "unknown")
    assert not service._inflight and not service._cache
    await service.lookup("1.2.3.4")
    assert provider.calls == 2


async def test_first_waiter_cancellation_does_not_cancel_other_waiters(make_service):
    provider = ControlledProvider()
    service = make_service(provider)
    first = asyncio.create_task(service.lookup("1.2.3.4"))
    second = asyncio.create_task(service.lookup("::ffff:1.2.3.4"))
    await provider.entered.wait()
    assert service._inflight["1.2.3.4"].waiters == 2
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert not provider.cancelled.is_set()
    assert service._inflight["1.2.3.4"].waiters == 1
    provider.release.set()
    assert (await second).status == "found"
    assert provider.calls == 1


async def test_all_waiters_cancel_and_new_request_waits_for_old_cleanup(make_service):
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()

    class CleanupProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            self.calls += 1
            self.entered.set()
            if self.calls > 1:
                return "fresh"
            try:
                await self.release.wait()
            finally:
                cleanup_started.set()
                await cleanup_release.wait()

    provider = CleanupProvider()
    service = make_service(provider)
    first, second = (asyncio.create_task(service.lookup("1.2.3.4")) for _ in range(2))
    await provider.entered.wait()
    try:
        first.cancel()
        second.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
        await cleanup_started.wait()
        flight = service._inflight["1.2.3.4"]
        assert flight.waiters == 0 and not flight.task.done()
        third = asyncio.create_task(service.lookup("1.2.3.4"))
        await asyncio.sleep(0)
        assert provider.calls == 1 and not third.done()
    finally:
        cleanup_release.set()
    assert (await third).location == "fresh"
    assert provider.calls == 2
    assert not service._inflight


async def test_deadline_includes_wait_for_retiring_query_cleanup(make_service):
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()

    class CleanupProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            self.calls += 1
            self.entered.set()
            try:
                await self.release.wait()
            finally:
                cleanup_started.set()
                await cleanup_release.wait()

    provider = CleanupProvider()
    service = make_service(provider, query_budget_seconds=0.03)
    first = asyncio.create_task(service.lookup("1.2.3.4"))
    await provider.entered.wait()
    first.cancel()
    await asyncio.gather(first, return_exceptions=True)
    await cleanup_started.wait()
    try:
        result = await service.lookup("1.2.3.4")
        assert result.status == "unavailable" and result.failures == ("chain:budget_exceeded",)
        assert provider.calls == 1
        assert not service._inflight["1.2.3.4"].task.done()
    finally:
        cleanup_release.set()
    await service.close()
    assert not service._inflight


@pytest.mark.parametrize(
    "error",
    [
        IpException(IpErrorCodes.QUERY_FAILED, context={"provider": "sample", "reason": "network"}),
        TypeError("provider bug"),
        TimeoutError("provider timeout bug"),
    ],
)
async def test_query_exception_is_shared_and_next_request_can_retry(make_service, error):
    class BrokenProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            await super().query(ip, remaining_seconds)
            raise error

    provider = BrokenProvider()
    service = make_service(provider, online_failure_policy="raise")
    queries = [asyncio.create_task(service.lookup("1.2.3.4")) for _ in range(8)]
    await provider.entered.wait()
    provider.release.set()
    failures = await asyncio.gather(*queries, return_exceptions=True)
    assert provider.calls == 1
    assert all(failure is error for failure in failures)
    assert not service._inflight and not service._cache
    with pytest.raises(type(error)):
        await service.lookup("1.2.3.4")
    assert provider.calls == 2


async def test_late_waiter_does_not_restart_shared_budget(make_service):
    provider = ControlledProvider()
    service = make_service(provider, query_budget_seconds=0.4)
    first = asyncio.create_task(service.lookup("1.2.3.4"))
    await provider.entered.wait()
    await asyncio.sleep(0.15)
    assert not first.done()
    started = monotonic()
    second = asyncio.create_task(service.lookup("1.2.3.4"))
    first_result, second_result = await asyncio.gather(first, second)
    assert first_result.status == second_result.status == "unavailable"
    assert second_result.failures == ("chain:budget_exceeded",)
    assert provider.calls == 1
    assert monotonic() - started < 0.35
    await service.close()
    assert provider.cancelled.is_set()


async def test_shared_tasks_have_no_request_context_and_do_not_cross_applications(make_service):
    request_identity = ContextVar("request_identity", default=None)
    observed = []

    class ContextProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            observed.append(request_identity.get())
            return await super().query(ip, remaining_seconds)

    first_provider, second_provider = ContextProvider("app1"), ContextProvider("app2")
    first_service, second_service = make_service(first_provider), make_service(second_provider)
    token = request_identity.set("sensitive request identity")
    try:
        first = asyncio.create_task(first_service.lookup("1.2.3.4"))
        second = asyncio.create_task(second_service.lookup("1.2.3.4"))
        await asyncio.gather(first_provider.entered.wait(), second_provider.entered.wait())
    finally:
        request_identity.reset(token)
    assert observed == [None, None]
    assert first_provider.calls == second_provider.calls == 1
    first_provider.release.set()
    second_provider.release.set()
    assert (await first).location == "app1" and (await second).location == "app2"


async def test_different_ips_can_query_concurrently(make_service):
    provider = ControlledProvider()
    service = make_service(provider)
    first = asyncio.create_task(service.lookup("1.2.3.4"))
    second = asyncio.create_task(service.lookup("8.8.8.8"))
    await provider.entered.wait()
    assert provider.calls == 2 and len(service._inflight) == 2
    provider.release.set()
    await asyncio.gather(first, second)


async def test_close_has_shared_terminal_wait_and_rejects_late_results(make_service):
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()

    class CleanupProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            self.calls += 1
            self.entered.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                cleanup_started.set()
                await cleanup_release.wait()
                return "late"

    provider = CleanupProvider()
    service = make_service(provider)
    query = asyncio.create_task(service.lookup("1.2.3.4"))
    await provider.entered.wait()
    first = asyncio.create_task(service.close())
    await cleanup_started.wait()
    try:
        second = asyncio.create_task(service.close())
        await asyncio.sleep(0)
        assert not first.done() and not second.done()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert not second.done()
        with pytest.raises(IpException):
            await service.lookup("8.8.8.8")
    finally:
        cleanup_release.set()
    await second
    with pytest.raises(IpException):
        await query
    assert not service._inflight and not service._cache


async def test_failure_after_every_waiter_cancelled_is_reported_once(make_service, monkeypatch):
    failures = []
    cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()
    failure = RuntimeError("cleanup failed after cancellation")

    class CaptureLogger:
        def opt(self, *, exception):
            failures.append(exception)
            return self

        def error(self, message):
            pass

    class BrokenCleanupProvider(ControlledProvider):
        async def query(self, ip, remaining_seconds):
            self.entered.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                cleanup_started.set()
                await cleanup_release.wait()
                raise failure

    monkeypatch.setattr("framework.starter_ip.service.ip_location_service.logger", CaptureLogger())
    provider = BrokenCleanupProvider()
    service = make_service(provider)
    query = asyncio.create_task(service.lookup("1.2.3.4"))
    await provider.entered.wait()
    query.cancel()
    await asyncio.gather(query, return_exceptions=True)
    await cleanup_started.wait()
    cleanup_release.set()
    await service.close()
    assert failures == [failure]
    assert not service._inflight
