from typing import Annotated

import pytest
from fastapi import Query
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from fixtures.public_web_app import create_public_app
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.base_vo import BaseVO
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result

pytestmark = pytest.mark.unit


def test_page_and_result_work_in_real_routes_with_runtime_configuration(config_dir):
    """从环境变量到查询解析再到公开响应，完整验证分页契约与模型过滤。"""
    app = create_public_app(
        base_dir=config_dir(), environ={"PAGE_DEFAULT_SIZE": "2", "PAGE_MAX_SIZE": "3"}
    )
    paginator = DataPaginator(app.state.bootstrap.page_settings)

    class RecordVO(BaseVO):
        record_id: int

    class Record:
        def __init__(self, record_id):
            self.record_id = record_id
            self.password = "private"

    @app.get("/records", response_model=Result[PageResult[RecordVO]])
    async def records(query: Annotated[PageQuery, Query()]):
        return Result.success(
            paginator.paginate_list([Record(i) for i in range(1, 6)], query).convert(RecordVO)
        )

    with TestClient(app) as client:
        response = client.get("/records", params={"page": 2})
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"code", "message", "data", "error"}
        assert body["code"] == 0 and body["message"] == "ok"
        assert body["data"] == {"items": [{"recordId": 3}, {"recordId": 4}], "total": 5}
        assert "password" not in response.text
        oversized = client.get("/records", params={"pageSize": 4})
        assert oversized.status_code == 200 and oversized.json()["code"] == 400
        assert oversized.json()["message"] == "pageSize 最大为 3"
        invalid = client.get("/records", params={"fetchAll": "true"})
        assert invalid.status_code == 200
        assert invalid.json()["code"] == 422
        schema = client.get("/openapi.json").json()
        assert "fetchAll" not in str(schema)
        assert "422" not in schema["paths"]["/records"]["get"]["responses"]


def test_response_configuration_is_applied_without_global_state(config_dir):
    """两个应用分别控制全量读取、文件内存限制和缓存策略。"""
    root = config_dir(
        {
            "page": {"default_size": 3},
            "response": {"download_cache": "private", "download_max_age": 20},
        }
    )
    first = create_public_app(
        base_dir=root,
        environ={
            "PAGE_FETCH_ALL_ENABLED": "true",
            "PAGE_FETCH_ALL_MAX_ROWS": "2",
            "RESPONSE_ATTACHMENT": "false",
            "RESPONSE_MAX_MEMORY_BYTES": "2",
            "RESPONSE_FILE_CHUNK_SIZE": "8",
        },
    ).state.bootstrap
    second = create_public_app(base_dir=root, environ={}).state.bootstrap
    assert first.page_settings.fetch_all_enabled is True
    assert second.page_settings.fetch_all_enabled is False
    assert first.response_settings.file_chunk_size == 8
    assert second.response_settings.file_chunk_size == 65536
    assert (
        DataPaginator(first.page_settings)
        .paginate_list([1, 2], PageQuery().enable_fetch_all())
        .total
        == 2
    )
    files = FileResult(first.response_settings)
    response = files.from_bytes(b"ok", "a.txt")
    assert response.headers["cache-control"] == "private, max-age=20"
    assert response.headers["content-disposition"].startswith("inline;")
    with pytest.raises(ValueError, match="内存下载超过"):
        files.from_bytes(b"big", "a.txt")
    assert FileResult(second.response_settings).from_bytes(b"big", "a.txt").body == b"big"


def test_lifespan_injects_same_translator_into_middleware_and_exception_handler(config_dir):
    """真实 ASGI 中间件共享本应用翻译器，关闭应用后释放两处引用。"""

    class GateMiddleware:
        def __init__(self, app, result):
            self.app = app
            self.result = result

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http" and scope["path"] == "/blocked":
                await self.result.send_error(
                    send,
                    GlobalErrorCodeConstants.UNAUTHORIZED,
                    accept_language=Headers(scope=scope).get("accept-language"),
                    headers={"WWW-Authenticate": "Bearer", "Vary": "Origin"},
                )
            else:
                await self.app(scope, receive, send)

    app = create_public_app(base_dir=config_dir(), environ={})
    context = app.state.bootstrap
    app.add_middleware(GateMiddleware, result=context.middleware_result)
    assert context.middleware_result.translator is None
    with TestClient(app) as client:
        assert context.middleware_result.translator is context.exception_handler.translator
        assert context.middleware_result.translator is not None
        response = client.get("/blocked", headers={"Accept-Language": "en-US"})
        expected = context.exception_handler.translator.translate_any_scope(
            "exception.unauthorized", "en-US"
        )
        assert response.status_code == 200
        assert response.json()["message"] == expected
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.headers["vary"] == "Origin, Accept-Language"
        assert client.get("/health").status_code == 200
    assert context.middleware_result.translator is context.exception_handler.translator is None


def test_disabled_i18n_keeps_middleware_default_message(config_dir):
    """关闭国际化时仍有可用中文提示，翻译器不成为强制外部服务。"""
    app = create_public_app(base_dir=config_dir({"i18n": {"enabled": False}}), environ={})
    with TestClient(app):
        content = app.state.bootstrap.middleware_result.build_error_content(
            GlobalErrorCodeConstants.BAD_REQUEST, accept_language="en-US"
        )
    assert content["message"] == GlobalErrorCodeConstants.BAD_REQUEST.description


@pytest.mark.parametrize(
    "environ",
    [
        {"PAGE_MAX_SIZE": "0"},
        {"PAGE_DEFAULT_SIZE": "201"},
        {"RESPONSE_FILE_CHUNK_SIZE": "0"},
        {"RESPONSE_DOWNLOAD_CACHE": "anything"},
    ],
)
def test_invalid_component_config_stops_app_creation(config_dir, environ):
    """无效开关和边界值不能静默回退为另一套运行参数。"""
    with pytest.raises(BootstrapConfigError):
        create_public_app(base_dir=config_dir(), environ=environ)
