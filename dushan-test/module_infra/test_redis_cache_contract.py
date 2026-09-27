import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from module_infra.dal.cache.cache.cache_monitor_dao import CacheMonitorDAO


async def test_cache_scan_uses_decoded_client_keys():
    async def scan_iter(**kwargs):
        yield "group:中文"
        yield "a"

    dao = CacheMonitorDAO()
    dao.manager = SimpleNamespace(get_client=lambda name: SimpleNamespace(scan_iter=scan_iter))
    assert await dao.scan_all_keys_in_db("default") == ["a", "group:中文"]


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("string", "中文值"),
        ("hash", {"字段": "值"}),
        ("list", ["值"]),
        ("set", ["值"]),
        ("zset", [{"member": "值", "score": 1.0}]),
        ("stream", [{"id": "1-0", "fields": {"字段": "值"}}]),
    ],
)
async def test_cache_detail_uses_decoded_strings_and_preserves_stream_values(kind, expected):
    client = SimpleNamespace(
        type=AsyncMock(return_value=kind),
        ttl=AsyncMock(return_value=60),
        getrange=AsyncMock(return_value="中文值"),
        strlen=AsyncMock(return_value=9),
        hscan=AsyncMock(return_value=(0, {"字段": "值"})),
        hlen=AsyncMock(return_value=1),
        lrange=AsyncMock(return_value=["值"]),
        llen=AsyncMock(return_value=1),
        sscan=AsyncMock(return_value=(0, ["值"])),
        scard=AsyncMock(return_value=1),
        zrange=AsyncMock(return_value=[("值", 1.0)]),
        zcard=AsyncMock(return_value=1),
        xrange=AsyncMock(return_value=[("1-0", {"字段": "值"})]),
        xlen=AsyncMock(return_value=1),
    )
    dao = CacheMonitorDAO()
    dao.manager = SimpleNamespace(get_client=lambda name: client)
    detail = await dao.get_key_detail("default", "example")
    assert detail.key_type == kind
    assert detail.ttl == 60
    assert (detail.value if kind == "string" else json.loads(detail.value)) == expected
    redacted = await dao.get_key_detail("default", "auth:token")
    assert redacted.value == "[redacted]"
