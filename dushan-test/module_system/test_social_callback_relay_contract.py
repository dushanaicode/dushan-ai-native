import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qsl, urlsplit

import pytest

from framework.starter_security.public import SecurityErrorCodes, SecurityException
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.service.social.social_client_service_impl import SocialClientServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def relay_service():
    """使用内存回调票据替身，避免访问真实缓存。"""
    service = SocialClientServiceImpl()
    service.cache_handler = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                hit=True,
                value={"redirect_uri": "https://app.example/callback", "code_parameter": "code"},
            )
        ),
        delete=AsyncMock(),
    )
    return service


@pytest.mark.parametrize("states", [[], ["a" * 64, "b" * 64], [""], ["a" * 63], ["a" * 65]])
async def test_relay_rejects_missing_duplicate_and_invalid_length_state(relay_service, states):
    """必须恰好一个 64 字符 state，不合规请求不得触碰缓存。"""
    parameters = [("state", state) for state in states] + [("code", "vendor-code")]
    with pytest.raises(SecurityException) as failure:
        await relay_service.relay_callback(parameters)
    assert failure.value.error_code == SecurityErrorCodes.INVALID
    relay_service.cache_handler.get.assert_not_awaited()
    relay_service.cache_handler.delete.assert_not_awaited()


@pytest.mark.parametrize("result", [("code", "vendor-code"), ("error", "access_denied")])
async def test_relay_consumes_unique_state_and_preserves_callback_parameters(relay_service, result):
    """校验通过后消费一次性 state，并只转交协议允许的参数。"""
    state = "a" * 64
    parameters = [("ignored", "vendor-extra"), ("state", state), result]
    target = await relay_service.relay_callback(parameters)
    key = hashlib.sha256(state.encode()).hexdigest()
    relay_service.cache_handler.get.assert_awaited_once_with(
        SystemCacheKeyConstants.SOCIAL_CALLBACK_RELAY, key
    )
    relay_service.cache_handler.delete.assert_awaited_once_with(
        SystemCacheKeyConstants.SOCIAL_CALLBACK_RELAY, key
    )
    parts = urlsplit(target)
    assert parts.scheme == "https" and parts.netloc == "app.example"
    assert parts.path == "/callback"
    assert parse_qsl(parts.query) == [("state", state), result]


@pytest.mark.parametrize(
    "results", [[("code", "one"), ("code", "two")], [], [("code", "one"), ("error", "denied")]]
)
async def test_relay_rejects_duplicate_or_ambiguous_results_without_consuming_state(
    relay_service, results
):
    """重复、缺失和互相冲突的回调结果不得消费一次性票据。"""
    with pytest.raises(SecurityException) as failure:
        await relay_service.relay_callback([("state", "a" * 64), *results])
    assert failure.value.error_code == SecurityErrorCodes.INVALID
    relay_service.cache_handler.delete.assert_not_awaited()
