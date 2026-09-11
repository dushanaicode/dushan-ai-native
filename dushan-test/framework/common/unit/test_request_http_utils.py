import base64

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import AliasChoices, BaseModel, Field

from framework.common.exception.core.exception_handler import GlobalExceptionHandler
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.utils.http.http_utils import HttpUtils
from framework.common.utils.request.request_utils import RequestUtils

pytestmark = pytest.mark.unit


def request(query=b"", headers=()):
    return Request(
        {"type": "http", "method": "GET", "path": "/", "query_string": query, "headers": headers}
    )


class Query(BaseRequestVO):
    tag_ids: list[int]
    keyword: str = ""


class ExplicitAlias(BaseModel):
    tags: list[str] = Field(validation_alias=AliasChoices("labels", "values"))


def test_query_lists_preserve_duplicates_single_values_and_aliases():
    assert RequestUtils.get_query_params(request(b"tagIds=1&tagIds=2&keyword=")) == {
        "tagIds": ["1", "2"],
        "keyword": "",
    }
    assert RequestUtils.validate_with_auto_list_params(request(b"tagIds=1"), Query).tag_ids == [1]
    assert RequestUtils.validate_with_auto_list_params(
        request(b"tagIds=1&tagIds=1"), Query
    ).tag_ids == [1, 1]
    assert RequestUtils.validate_with_auto_list_params(
        request(b"labels=one"), ExplicitAlias
    ).tags == ["one"]
    assert RequestUtils.validate_with_auto_list_params(
        request(b"values=one"), ExplicitAlias
    ).tags == ["one"]
    with pytest.raises(RequestValidationError):
        RequestUtils.validate_with_auto_list_params(request(b"tagIds=bad"), Query)
    with pytest.raises(RequestValidationError):
        RequestUtils.validate_with_auto_list_params(request(b"tagIds=1&keyword=a&keyword=b"), Query)


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


def test_query_validation_uses_existing_business_response_contract():
    app = FastAPI()
    GlobalExceptionHandler(debug=False).register(app)

    @app.get("/search")
    def search(req: Request):
        return RequestUtils.validate_with_auto_list_params(req, Query).model_dump()

    with TestClient(app) as client:
        response = client.get("/search?tagIds=bad")
    assert response.status_code == 200
    assert response.json()["error"]["fields"][0]["field"] == "tagIds[0]"
    assert response.json()["code"] != 0
