import asyncio
from time import monotonic

import pytest

from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.exception.ip_provider_error import IpProviderError
from framework.starter_ip.service.ip_location_service import IpLocationService
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


class SampleProvider(IpLocationProvider):
    name = "sample"
    online = True

    def __init__(self, result="地区", error=None):
        self.result, self.error = result, error
        self.calls = 0
        self.budgets = []

    async def query(self, ip, remaining_seconds):
        self.calls += 1
        self.budgets.append(remaining_seconds)
        if self.error is not None:
            raise self.error
        return self.result


def create_service(ip_settings, providers, **overrides):
    settings = ip_settings(
        local_enabled=False,
        online_enabled=True,
        online_providers=[provider.name for provider in providers],
        **overrides,
    )
    service = IpLocationService(settings, providers)
    service.open()
    return service


@pytest.mark.parametrize(
    "ip,status",
    [
        ("127.0.0.1", "loopback"),
        ("::1", "loopback"),
        ("192.168.1.2", "private"),
        ("fd00::1", "private"),
        ("fe80::1", "link_local"),
        ("169.254.1.2", "link_local"),
        ("192.0.2.1", "reserved"),
        ("2001:db8::1", "reserved"),
        ("224.0.0.1", "reserved"),
        ("100.64.0.1", "reserved"),
    ],
)
async def test_non_public_addresses_never_reach_providers(ip_settings, ip, status):
    provider = SampleProvider()
    service = create_service(ip_settings, [provider])
    assert (await service.lookup(ip)).status == status
    assert provider.calls == 0
    with pytest.raises(ValueError):
        await service.lookup("invalid")


async def test_local_first_and_online_requires_opt_in(ip_settings):
    local, online = SampleProvider(None), SampleProvider("在线")
    local.name, local.online = "local", False
    settings = ip_settings(online_enabled=False)
    service = IpLocationService(settings, [online, local])
    service.open()
    assert (await service.lookup("1.2.3.4")).status == "unknown"
    assert local.calls == 1 and online.calls == 0
    local.result = "本地"
    enabled = IpLocationService(
        ip_settings(online_enabled=True, online_providers=["sample"]), [online, local]
    )
    enabled.open()
    result = await enabled.lookup("1.2.3.4")
    assert result.location == "本地" and result.provider == "local"
    assert online.calls == 0


async def test_unknown_unavailable_and_failure_policy_are_distinct(ip_settings):
    unknown = create_service(ip_settings, [SampleProvider(None)])
    assert (await unknown.lookup("1.2.3.4")).status == "unknown"
    error = IpProviderError("sample", "network")
    unavailable = create_service(ip_settings, [SampleProvider(error=error)])
    result = await unavailable.lookup("1.2.3.4")
    assert result.status == "unavailable" and result.failures == ("sample:network",)
    assert not unavailable._cache
    strict = create_service(
        ip_settings, [SampleProvider(error=error)], online_failure_policy="raise"
    )
    with pytest.raises(IpProviderError) as caught:
        await strict.lookup("1.2.3.4")
    assert caught.value is error
    broken = create_service(ip_settings, [SampleProvider(error=TypeError("programming failure"))])
    with pytest.raises(TypeError, match="programming"):
        await broken.lookup("1.2.3.4")


async def test_continue_returns_next_provider_and_records_failure(ip_settings):
    first, second = (
        SampleProvider(error=IpProviderError("first", "network")),
        SampleProvider("第二路"),
    )
    first.name, second.name = "first", "second"
    service = create_service(ip_settings, [first, second])
    result = await service.lookup("1.2.3.4")
    assert result.provider == "second" and result.location == "第二路"
    assert result.failures == ("first:network",)
    assert 0 < second.budgets[0] <= first.budgets[0]


async def test_total_budget_cancels_active_provider(ip_settings):
    cancelled = asyncio.Event()

    class SlowProvider(SampleProvider):
        async def query(self, ip, remaining_seconds):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    service = create_service(ip_settings, [SlowProvider()], query_budget_seconds=0.02)
    started = monotonic()
    result = await service.lookup("1.2.3.4")
    assert result.status == "unavailable" and result.failures == ("chain:budget_exceeded",)
    await service.close()
    assert cancelled.is_set()
    assert monotonic() - started < 1


async def test_caller_cancellation_does_not_leave_background_queries(ip_settings):
    entered, cancelled = asyncio.Event(), asyncio.Event()

    class SlowProvider(SampleProvider):
        async def query(self, ip, remaining_seconds):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    service = create_service(ip_settings, [SlowProvider()])
    query = asyncio.create_task(service.lookup("1.2.3.4"))
    await entered.wait()
    query.cancel()
    with pytest.raises(asyncio.CancelledError):
        await query
    assert cancelled.is_set() and not service._cache


async def test_cache_has_ttl_size_limit_and_application_isolation(ip_settings, monkeypatch):
    provider = SampleProvider()
    first = create_service(ip_settings, [provider], cache_max_size=1, cache_ttl_seconds=10)
    second = create_service(ip_settings, [provider], cache_max_size=1)
    await first.lookup("1.2.3.4")
    await first.lookup("::ffff:1.2.3.4")
    assert provider.calls == 1
    await second.lookup("1.2.3.4")
    assert provider.calls == 2
    await first.lookup("8.8.8.8")
    assert list(first._cache) == ["8.8.8.8"]
    monkeypatch.setattr(
        "framework.starter_ip.service.ip_location_service.monotonic", lambda: monotonic() + 11
    )
    await first.lookup("8.8.8.8")
    assert provider.calls == 4
    await first.close()
    assert not first._cache and second._cache
    with pytest.raises(IpException):
        await first.lookup("8.8.8.8")


async def test_unknown_cache_can_be_disabled_and_no_provider_is_unavailable(ip_settings):
    provider = SampleProvider(None)
    service = create_service(ip_settings, [provider], unknown_cache_ttl_seconds=0)
    await service.lookup("1.2.3.4")
    await service.lookup("1.2.3.4")
    assert provider.calls == 2 and not service._cache
    absent = IpLocationService(ip_settings(local_enabled=False, online_enabled=False), [])
    absent.open()
    assert (await absent.lookup("1.2.3.4")).failures == ("no_provider",)


async def test_service_close_rejects_late_result_and_does_not_repopulate_cache(ip_settings):
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowProvider(SampleProvider):
        async def query(self, ip, remaining_seconds):
            entered.set()
            await release.wait()
            return "late"

    service = create_service(ip_settings, [SlowProvider()])
    query = asyncio.create_task(service.lookup("1.2.3.4"))
    await entered.wait()
    await service.close()
    release.set()
    with pytest.raises(IpException):
        await query
    assert not service._cache
