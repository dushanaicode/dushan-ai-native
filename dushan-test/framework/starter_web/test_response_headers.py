import pytest

from framework.starter_web.response.response_headers import ResponseHeaders

pytestmark = pytest.mark.unit


def test_no_store_replaces_cache_policy_without_mutating_input_headers():
    """禁止存储时覆盖旧缓存策略，同时保留其他响应头且不修改输入。"""
    headers = {"CACHE-Control": "public, max-age=60", "Retry-After": "3"}

    assert ResponseHeaders.with_no_store(headers) == {
        "cache-control": "no-store",
        "retry-after": "3",
    }
    assert headers == {"CACHE-Control": "public, max-age=60", "Retry-After": "3"}
    assert ResponseHeaders.with_no_store() == {"cache-control": "no-store"}
