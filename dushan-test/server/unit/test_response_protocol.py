from typing import Annotated
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.testclient import TestClient
from pydantic import Field, HttpUrl

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.field_error import FieldError
from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.exception.exceptions.model_validator_exception import ModelValidatorException
from framework.common.exception.exceptions.remote_service_exception import RemoteServiceException
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.exception.utils.validation_error_mapper import ValidationErrorMapper
from framework.common.page.schemas.page_query import PageQuery
from framework.common.response.core.result import Result
from framework.common.schemas.base_request_vo import BaseRequestVO
from server.starter_server import create_app

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "locale,message", [("zh-CN", "数值不能小于 0"), ("en-US", "The value must be at least 0")]
)
def test_nested_request_errors_are_public_localized_and_form_addressable(
    config_dir, locale, message
):
    """嵌套数组校验错误可定位表单，原始输入和校验上下文不进入响应。"""

    class Contact(BaseRequestVO):
        user_age: Annotated[int, Field(ge=0)]

    class RequestVO(BaseRequestVO):
        contacts: list[Contact]
        password: Annotated[str, Field(min_length=30)]

    app = create_app(base_dir=config_dir(), environ={})

    @app.post("/submit", response_model=Result[bool])
    async def submit(request: RequestVO):
        return Result.success(True)

    with TestClient(app) as client:
        response = client.post(
            "/submit",
            json={"contacts": [{"userAge": -1}], "password": "private-input"},
            headers={"Accept-Language": locale},
        )
    assert response.status_code == 200
    assert set(response.json()) == {"code", "message", "data", "error"}
    assert response.json()["code"] == 422 and response.json()["data"] is None
    fields = response.json()["error"]["fields"]
    assert fields[0] == {"field": "contacts[0].userAge", "message": message}
    assert fields[1]["field"] == "password"
    assert all(set(field) == {"field", "message"} for field in fields)
    assert "private-input" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_development_debug_keeps_json_contract_and_internal_failures_classified(config_dir):
    """开发debug不启用框架裸堆栈，响应模型错误仍是系统故障而非表单字段错误。"""
    app = create_app(base_dir=config_dir({"server": {"debug": True}}), environ={})

    @app.get("/broken", response_model=Result[int])
    async def broken():
        return {"code": 0, "message": "ok", "data": "not-an-integer", "error": None}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/broken")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 500
    assert set(body) == {"code", "message", "data", "error"}
    assert "debug" in body["error"] and "fields" not in body["error"]
    assert app.debug is False and app.state.bootstrap.settings.debug is True


@pytest.mark.parametrize(
    "exception_type", [ModelValidatorException, ServiceException, RemoteServiceException]
)
def test_business_services_can_explicitly_attach_field_errors(config_dir, exception_type):
    """业务字段错误有显式入口，私有context不被推断为公开详情。"""
    app = create_app(base_dir=config_dir(), environ={})

    @app.post("/conflict")
    async def conflict():
        fields = [FieldError(field="username", message="该用户名已存在")]
        arguments = (
            (GlobalErrorCodeConstants.CONFLICT,) if exception_type is ServiceException else ()
        )
        raise exception_type(
            *arguments, field_errors=fields, context={"password": "private-context"}
        )

    with TestClient(app) as client:
        response = client.post("/conflict")
    assert response.status_code == 200 and response.json()["code"] != 0
    assert response.json()["error"]["fields"] == [
        {"field": "username", "message": "该用户名已存在"}
    ]
    if exception_type is RemoteServiceException:
        assert response.json()["error"]["retryable"] is True
    assert "private-context" not in response.text


def test_special_protocols_keep_http_status_and_public_page_names_are_strict(config_dir, tmp_path):
    """标准文件与跳转状态保留，旧分页名字不会被静默接受。"""
    file = tmp_path / "download.txt"
    file.write_bytes(b"abcdef")
    app = create_app(base_dir=config_dir(), environ={})

    @app.get("/download")
    async def download():
        return FileResponse(file)

    @app.get("/redirect")
    async def redirect():
        return RedirectResponse("/health")

    @app.get("/redirect-exception")
    async def redirect_exception():
        raise HTTPException(307, headers={"Location": "/health"})

    @app.post("/page")
    async def page(request: PageQuery):
        return Result.success(request)

    with TestClient(app) as client:
        assert client.get("/download", headers={"Range": "bytes=1-3"}).status_code == 206
        assert client.get("/download", headers={"Range": "bytes=99-"}).status_code == 416
        for path in ("/redirect", "/redirect-exception"):
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 307 and response.headers["location"] == "/health"
        assert client.post("/page", json={"page": 2, "pageSize": 3}).json()["data"] == {
            "page": 2,
            "pageSize": 3,
        }
        for old_name in ("pageNo", "page_no"):
            response = client.post("/page", json={old_name: 2})
            assert response.status_code == 200 and response.json()["code"] == 422


@pytest.mark.parametrize(
    "location,expected",
    [
        (("body", "contacts", 0, "phoneNumber"), "contacts[0].phoneNumber"),
        (("body", "literal.name"), '["literal.name"]'),
        (("body",), ""),
        (("header", "x-request"), 'header["x-request"]'),
    ],
)
def test_field_paths_keep_arrays_and_literal_field_names_distinct(location, expected):
    """路径规范化保留特殊字符语义，不把字面点号变成另一个嵌套字段。"""
    assert ValidationErrorMapper.field_path(location) == expected


@pytest.mark.parametrize(
    "arguments,expected",
    [
        ({}, "Invalid request parameters"),
        ({"msg": "pageSize 最大为 200"}, "pageSize 最大为 200"),
        ({"msg": "请求参数不正确"}, "请求参数不正确"),
        ({"msg": "   "}, "Invalid request parameters"),
        ({"msg": "资源 {} 不可用", "format_args": (7,)}, "资源 7 不可用"),
        ({"msg": "最终提示", "message_key": "exception.not_found"}, "Request not found"),
        (
            {
                "msg": "默认提示",
                "message_key": "validation.greater_than_equal",
                "format_args": (3,),
            },
            "The value must be at least 3",
        ),
        (
            {"msg": "错误 {", "message_key": "exception.not_found", "format_args": (3,)},
            "请求参数不正确",
        ),
    ],
)
def test_business_message_priority_survives_the_application_translation_chain(
    config_dir, arguments, expected
):
    """消息来源决定翻译优先级，显式提示即使等于默认文案也不能被改写。"""
    app = create_app(base_dir=config_dir(), environ={})

    @app.get("/business-message")
    async def business_message():
        raise IllegalArgumentException(**arguments)

    with TestClient(app) as client:
        response = client.get("/business-message", headers={"Accept-Language": "en-US"})
    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert response.json()["message"] == expected


@pytest.mark.parametrize(
    "locale,format_message,type_message",
    [
        ("zh-CN", "格式不正确", "值的类型不正确"),
        ("en-US", "The format is invalid", "The value has an invalid type"),
    ],
)
def test_url_and_uuid_format_errors_are_distinct_from_integer_parsing_errors(
    config_dir, locale, format_message, type_message
):
    """使用真实 Pydantic 错误经 HTTP 响应验证格式与类型分类，以及双语字段提示。"""

    class RequestVO(BaseRequestVO):
        homepage: HttpUrl
        record_id: UUID
        age: int

    app = create_app(base_dir=config_dir(), environ={})

    @app.post("/validate-format", response_model=Result[bool])
    async def validate_format(request: RequestVO):
        return Result.success(True)

    with TestClient(app) as client:
        response = client.post(
            "/validate-format",
            json={"homepage": "not-a-url", "recordId": "not-a-uuid", "age": "not-an-integer"},
            headers={"Accept-Language": locale},
        )
    assert response.status_code == 200 and response.json()["code"] == 422
    assert response.json()["error"]["fields"] == [
        {"field": "homepage", "message": format_message},
        {"field": "recordId", "message": format_message},
        {"field": "age", "message": type_message},
    ]
