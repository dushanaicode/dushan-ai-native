from typing import Annotated

import pytest
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.testclient import TestClient

from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.common.response.core.result import Result
from framework.common.schemas.base_vo import BaseVO
from server.starter_server import create_app

pytestmark = pytest.mark.unit


def resolve_ref(document, schema):
    """按 JSON Pointer 解析 schema 引用，检查声明确实指向文档中的模型。"""
    if "$ref" not in schema:
        return schema
    target = document
    for key in schema["$ref"].removeprefix("#/").split("/"):
        target = target[key.replace("~1", "/").replace("~0", "~")]
    return target


def test_openapi_keeps_typed_pagination_and_describes_actual_validation_response(config_dir):
    """文档中的成功分页模型与实际 200 字段错误同时可用，引用不会悬空。"""

    class RecordVO(BaseVO):
        record_id: int

    app = create_app(base_dir=config_dir(), environ={})

    @app.get("/records", response_model=Result[PageResult[RecordVO]])
    async def records(query: Annotated[PageQuery, Query()]):
        return Result.success(PageResult(items=[RecordVO(record_id=1)], total=1))

    with TestClient(app) as client:
        response = client.get("/records", params={"page": 0})
        document = client.get("/openapi.json").json()
    responses = document["paths"]["/records"]["get"]["responses"]
    assert response.status_code == 200 and response.json()["code"] == 422
    assert "422" not in responses
    alternatives = responses["200"]["content"]["application/json"]["schema"]["anyOf"]
    assert len(alternatives) == 2
    success = resolve_ref(document, alternatives[0])
    page = resolve_ref(document, success["properties"]["data"]["anyOf"][0])
    assert set(page["properties"]) == {"items", "total"}
    row = resolve_ref(document, page["properties"]["items"]["items"])
    assert set(row["properties"]) == {"recordId"}
    error = resolve_ref(document, alternatives[1])
    assert set(error["required"]) == set(response.json()) == {"code", "message", "data", "error"}
    assert error["properties"]["code"]["not"] == {"const": 0}
    assert error["properties"]["data"]["type"] == "null"
    details = resolve_ref(document, error["properties"]["error"]["anyOf"][0])
    field = resolve_ref(document, details["properties"]["fields"]["items"])
    assert set(field["properties"]) == {"field", "message"}
    assert response.json()["error"]["fields"][0]["field"] == "page"


def test_openapi_preserves_special_statuses_media_and_explicit_responses(config_dir, tmp_path):
    """文件和跳转保留协议状态，默认参数错误补充为 JSON 200，显式响应声明不被删除。"""
    app = create_app(base_dir=config_dir(), environ={})
    file = tmp_path / "download.bin"
    file.write_bytes(b"abcdef")
    binary = {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}
    range_response = {
        "description": "部分文件",
        "content": binary,
        "headers": {"Content-Range": {"schema": {"type": "string"}}},
    }

    @app.get(
        "/download",
        response_class=FileResponse,
        responses={200: {"content": binary}, 206: range_response, 416: {"description": "范围无效"}},
    )
    async def download(version: int = 1):
        return FileResponse(file)

    @app.get("/redirect", response_class=RedirectResponse, status_code=307)
    async def redirect(version: int = 1):
        return RedirectResponse("/health")

    @app.get("/probe", responses={503: {"description": "尚未就绪"}})
    async def probe(ready: bool = True):
        return JSONResponse({"ready": ready}, status_code=200 if ready else 503)

    explicit = {
        "description": "显式协议错误",
        "content": {"application/json": {"schema": {"type": "string"}}},
    }

    @app.get("/explicit", responses={422: explicit})
    async def explicit_response(version: int = 1):
        return JSONResponse("invalid", status_code=422)

    with TestClient(app) as client:
        document = client.get("/openapi.json").json()
        assert client.get("/download", headers={"Range": "bytes=1-3"}).status_code == 206
        assert client.get("/download", headers={"Range": "bytes=99-"}).status_code == 416
        invalid = client.get("/download", params={"version": "bad"})
        assert invalid.status_code == 200 and invalid.json()["code"] == 422
        assert client.get("/redirect", follow_redirects=False).status_code == 307
        assert client.get("/probe", params={"ready": "false"}).status_code == 503
    download_responses = document["paths"]["/download"]["get"]["responses"]
    assert "422" not in download_responses
    assert (
        download_responses["200"]["content"]["application/octet-stream"]
        == binary["application/octet-stream"]
    )
    assert "application/json" in download_responses["200"]["content"]
    assert download_responses["206"] == range_response
    assert download_responses["416"]["description"] == "范围无效"
    assert "307" in document["paths"]["/redirect"]["get"]["responses"]
    assert document["paths"]["/probe"]["get"]["responses"]["503"]["description"] == "尚未就绪"
    assert document["paths"]["/explicit"]["get"]["responses"]["422"] == explicit


def test_openapi_cache_and_included_routes_remain_per_application(config_dir):
    """原生缓存失效后处理新增路由，重复读取不嵌套 schema，应用之间没有共享状态。"""
    root = config_dir()
    first = create_app(base_dir=root, environ={})
    second = create_app(base_dir=root, environ={})
    router = APIRouter()

    @router.get("/included", response_model=Result[int])
    async def included(value: int):
        return Result.success(value)

    initial = first.openapi()
    assert first.openapi() is initial
    first.include_router(router, prefix="/api")
    updated = first.openapi()
    assert updated is not initial
    assert first.openapi() is updated
    operation = updated["paths"]["/api/included"]["get"]
    assert "422" not in operation["responses"]
    alternatives = operation["responses"]["200"]["content"]["application/json"]["schema"]["anyOf"]
    assert len(alternatives) == 2 and "$ref" in alternatives[0]
    assert "/api/included" not in second.openapi()["paths"]
    first.openapi_schema = None
    rebuilt = first.openapi()
    assert rebuilt is not updated
    assert rebuilt["paths"]["/api/included"]["get"] == operation
