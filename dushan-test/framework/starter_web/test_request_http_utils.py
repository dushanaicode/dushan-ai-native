import base64

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from framework.starter_web.utils.http_utils import HttpUtils
from framework.starter_web.utils.request_utils import RequestUtils

pytestmark = pytest.mark.unit


def request(query=b"", headers=()):
    return Request(
        {"type": "http", "method": "GET", "path": "/", "query_string": query, "headers": headers}
    )


def test_query_params_preserve_single_values_duplicates_and_empty_values():
    assert RequestUtils.get_query_params(request(b"tagIds=1")) == {"tagIds": "1"}
    assert RequestUtils.get_query_params(request(b"tagIds=1&tagIds=2&keyword=")) == {
        "tagIds": ["1", "2"],
        "keyword": "",
    }


def test_indexed_arrays_sort_and_keep_empty_entries():
    parsed = HttpUtils.preprocess_array_query_params(
        request(b"ids[9]=last&ids[0]=&other=a&other=b&ids[2]=middle")
    )
    assert parsed == {"ids": ["", "middle", "last"], "other": ["a", "b"]}
    for query in (b"ids[0]=a&ids[0]=b", b"ids=a&ids[0]=b"):
        with pytest.raises(RequestValidationError):
            HttpUtils.preprocess_array_query_params(request(query))


def test_explicit_index_mapping_applies_to_one_or_many_values():
    assert RequestUtils.process_multi_params(request(b"tags=a"), {"tags": "tags[%d]"}) == {
        "tags[0]": "a"
    }
    with pytest.raises(RequestValidationError):
        RequestUtils.process_multi_params(request(b"tags=a&tags[0]=b"), {"tags": "tags[%d]"})


def test_indexed_array_does_not_allocate_by_index_or_parse_huge_integers():
    query = b"ids[" + b"9" * 5000 + b"]=last&ids[0]=first"
    assert HttpUtils.preprocess_array_query_params(request(query)) == {"ids": ["first", "last"]}


def test_urls_preserve_query_duplicates_blank_values_and_fragment():
    with pytest.raises(ValueError, match="重名"):
        HttpUtils.append_query("https://host/", {"a": 1, "b": 2}, keys_map={"a": "x", "b": "x"})
    assert (
        HttpUtils.replace_url_query("https://host/p?a=&b=1&b=2#part", "x", 3)
        == "https://host/p?a=&b=1&b=2&x=3#part"
    )
    assert (
        HttpUtils.build_url("https://host/base?a=#part", "next", {"ids": [1, 2]})
        == "https://host/base/next?a=&ids=1&ids=2#part"
    )
    assert (
        HttpUtils.append_query("https://host/#a=1", {"x": 2}, to_fragment=True)
        == "https://host/#a=1&x=2"
    )
    assert HttpUtils.parse_cookie_string('a="hello world"; b=2') == {"a": "hello world", "b": "2"}


@pytest.mark.parametrize(
    "header", [b"", b"Bearer token", b"Basic ???", b"Basic abc", b"Basic YQ=="]
)
def test_invalid_basic_credentials_never_authenticate(header):
    assert (
        HttpUtils.obtain_basic_authorization(request(headers=[(b"authorization", header)])) is None
    )


def test_oauth_basic_credentials_decode_form_components():
    encoded = base64.b64encode(b"client%3Aid:s%2Be+cret")
    assert HttpUtils.obtain_basic_authorization(
        request(headers=[(b"authorization", b"Basic " + encoded)])
    ) == ("client:id", "s+e cret")
    encoded = base64.b64encode(b"client:%GG")
    assert (
        HttpUtils.obtain_basic_authorization(
            request(headers=[(b"authorization", b"Basic " + encoded)])
        )
        is None
    )
