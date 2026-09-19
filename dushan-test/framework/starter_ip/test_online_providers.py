import asyncio
import json

import httpx
import pytest

from framework.starter_ip.client.ip_location_http_client import IpLocationHttpClient
from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.provider.pconline_ip_location_provider import PconlineIpLocationProvider
from framework.starter_ip.provider.vore_ip_location_provider import VoreIpLocationProvider
from framework.starter_ip.service.area_service import AreaService
from framework.starter_ip.service.ip_location_service import IpLocationService
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider
from framework.starter_ip.starter.ip_starter import IpStarter


def create_client(settings, handler):
    client = IpLocationHttpClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


async def test_pconline_gbk_result_status_and_echo(ip_settings):
    data = {"ip": "1.2.3.4", "pro": "广东省", "city": "深圳市", "err": "", "future_field": 1}
    settings = ip_settings(online_enabled=True)
    client = create_client(
        settings,
        lambda request: httpx.Response(
            200, content=json.dumps(data, ensure_ascii=False).encode("gbk")
        ),
    )
    provider = PconlineIpLocationProvider(settings, client)
    try:
        assert await provider.query("1.2.3.4", 1) == "广东-深圳"
        data.update(pro="", city="", err="noprovince")
        assert await provider.query("1.2.3.4", 1) is None
        data["ip"] = "8.8.8.8"
        with pytest.raises(IpException, match="查询失败"):
            await provider.query("1.2.3.4", 1)
    finally:
        await client.close()


async def test_vore_ipv6_schema_and_echo(ip_settings):
    data = {
        "code": 200,
        "msg": "SUCCESS",
        "ipinfo": {"text": "2604:a840:3:0:0:0:0:a04d", "type": "ipv6"},
        "adcode": {"p": "", "c": ""},
        "ipdata": {"info1": "United States", "info2": "California"},
    }
    settings = ip_settings(online_enabled=True)
    client = create_client(settings, lambda request: httpx.Response(200, json=data))
    provider = VoreIpLocationProvider(settings, client)
    try:
        assert await provider.query("2604:a840:3::a04d", 1) == "United States-California"
        data["code"] = True
        with pytest.raises(IpException) as failure:
            await provider.query("2604:a840:3::a04d", 1)
        assert failure.value.context["reason"] == "protocol"
    finally:
        await client.close()


@pytest.mark.parametrize(
    "status,body,reason",
    [(302, b"", "http_status"), (500, b"", "http_status"), (200, b"x" * 101, "response_too_large")],
)
async def test_http_status_and_response_resource_bounds(ip_settings, status, body, reason):
    settings = ip_settings(online_enabled=True, online_max_response_bytes=100)
    client = create_client(settings, lambda request: httpx.Response(status, content=body))
    try:
        with pytest.raises(IpException) as failure:
            await client.get("sample", "https://example.org", params={}, timeout_seconds=1)
        assert failure.value.context["reason"] == reason
    finally:
        underlying = client._client
        await client.close()
        assert underlying.is_closed and client._client is None


async def test_real_client_open_close_and_multi_application_isolation(ip_settings):
    settings = ip_settings(online_enabled=True)
    first, second = IpLocationHttpClient(settings), IpLocationHttpClient(settings)
    first.open()
    second.open()
    first_raw, second_raw = first._client, second._client
    await first.close()
    assert first_raw.is_closed and not second_raw.is_closed
    await second.close()
    disabled = IpLocationHttpClient(ip_settings(online_enabled=False))
    with pytest.raises(ValueError, match="未启用"):
        disabled.open()
    assert disabled._client is None


async def test_stream_is_closed_at_body_limit_and_compression_is_rejected(ip_settings):
    class ObservedStream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield b"x" * 60
            yield b"x" * 60

        async def aclose(self):
            self.closed = True

    settings = ip_settings(online_enabled=True, online_max_response_bytes=100)
    stream = ObservedStream()
    client = create_client(settings, lambda request: httpx.Response(200, stream=stream))
    try:
        with pytest.raises(IpException) as failure:
            await client.get("sample", "https://example.org", params={}, timeout_seconds=1)
        assert failure.value.context["reason"] == "response_too_large" and stream.closed
    finally:
        await client.close()

    compressed = create_client(
        settings,
        lambda request: httpx.Response(
            200, stream=ObservedStream(), headers={"Content-Encoding": "gzip"}
        ),
    )
    try:
        with pytest.raises(IpException) as failure:
            await compressed.get("sample", "https://example.org", params={}, timeout_seconds=1)
        assert failure.value.context["reason"] == "content_encoding"
    finally:
        await compressed.close()


async def test_concurrent_http_close_waits_for_same_terminal_task(ip_settings):
    settings = ip_settings(online_enabled=True)
    client = IpLocationHttpClient(settings)
    client.open()
    original = client._client
    original_close = original.aclose
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_close():
        entered.set()
        await release.wait()
        await original_close()

    original.aclose = paused_close
    first = asyncio.create_task(client.close())
    await entered.wait()
    second = asyncio.create_task(client.close())
    await asyncio.sleep(0)
    assert not first.done() and not second.done()
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert not second.done()
    release.set()
    await second
    assert original.is_closed


async def test_repeated_cancellation_waits_for_real_cleanup(ip_settings):
    settings = ip_settings(online_enabled=True)
    started, release = asyncio.Event(), asyncio.Event()
    client = IpLocationHttpClient(settings)
    client.open()
    original = client._client
    original_close = original.aclose

    async def slow_close():
        started.set()
        await release.wait()
        await original_close()

    original.aclose = slow_close
    areas, database = AreaService(), Ip2RegionDatabase()
    areas.initialize()
    database.initialize(("ipv4", "ipv6"))
    service = IpLocationService(settings, [])
    starter = IpStarter(settings, areas, database, client, service)
    close_task = asyncio.create_task(starter.close())
    await started.wait()
    close_task.cancel()
    await asyncio.sleep(0)
    close_task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await close_task
    assert original.is_closed and database._searchers is None and areas._areas is None


async def test_starter_waits_for_shared_query_cleanup_before_http_and_xdb_close(ip_settings):
    settings = ip_settings(
        online_enabled=True, online_providers=["sample"], local_families=["ipv4"]
    )
    entered, cleanup_started, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    client = IpLocationHttpClient(settings)
    areas, database = AreaService(), Ip2RegionDatabase()

    class ResourceProvider(IpLocationProvider):
        name, online = "sample", True

        async def query(self, ip, remaining_seconds):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await release.wait()
                assert not raw_client.is_closed
                assert database.search("1.2.3.4")
                assert areas.get_area(110101) is not None

    location = IpLocationService(settings, [ResourceProvider()])
    starter = IpStarter(settings, areas, database, client, location)
    await starter.open()
    raw_client = client._client
    query = asyncio.create_task(location.lookup("1.2.3.4"))
    await entered.wait()
    shutdown = asyncio.create_task(starter.close())
    await cleanup_started.wait()
    try:
        assert not shutdown.done() and not raw_client.is_closed
        assert database._searchers is not None and areas._areas is not None
        shutdown.cancel()
        await asyncio.sleep(0)
        shutdown.cancel()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await shutdown
    with pytest.raises(IpException):
        await query
    assert raw_client.is_closed and database._searchers is None and areas._areas is None
    assert not location._inflight
