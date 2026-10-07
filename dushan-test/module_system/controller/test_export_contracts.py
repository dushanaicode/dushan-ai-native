import importlib
import inspect
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.params import Query
from fastapi.routing import APIRoute, _iter_routes_with_context
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from fixtures.config_factory import ConfigFactory
from framework.common.page import PageQuery, PageResult, PageSettings
from framework.common.schemas.request import ExportFieldsReqVO
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.core.excel_schema import ExcelSchema
from framework.starter_excel.public import (
    DictConverter,
    ExcelReader,
    ExcelWriter,
    IdsConverter,
)
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.public import FileResult
from module_system.controller.admin.user import user_controller as user_module
from module_system.controller.admin.user.vo.user.user_import_resp_vo import UserImportRespVO

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("module_name,expected_count", [("module_system", 14), ("module_infra", 9)])
def test_export_routes_share_query_model_and_only_consumed_providers(module_name, expected_count):
    router = importlib.import_module(f"{module_name}.router").admin_router_main
    count = 0
    for route, _ in _iter_routes_with_context(router.routes):
        if not isinstance(route, APIRoute) or not route.path.endswith("/export-excel"):
            continue
        parameters = inspect.signature(route.endpoint).parameters
        request_type = get_type_hints(route.endpoint)["page_req_vo"]
        assert isinstance(parameters["page_req_vo"].default, Query), route.path
        assert issubclass(request_type, ExportFieldsReqVO), route.path
        assert request_type.__name__.endswith("ExportReqVO"), route.path
        page_type = next(base for base in request_type.__bases__ if issubclass(base, PageQuery))
        assert "fields" not in page_type.model_fields, route.path
        assert "request" not in parameters and "fields" not in parameters, route.path
        assert "page_settings" not in parameters, route.path

        controller = importlib.import_module(route.endpoint.__module__)
        response_type = getattr(controller, request_type.__name__.replace("ExportReqVO", "RespVO"))
        required_providers = set()
        for column in ExcelSchema(response_type).export_columns().values():
            if isinstance(column.converter, DictConverter):
                required_providers.add("dictionaries")
            elif isinstance(column.converter, IdsConverter):
                required_providers.add(column.converter.kind)
        actual_providers = {"dictionaries", "departments", "posts", "areas"} & parameters.keys()
        assert actual_providers == required_providers, route.path
        count += 1
    assert count == expected_count


@pytest.mark.parametrize(
    "module_name,router_name,service_name,method_name,filters,expected",
    [
        (
            "module_system.controller.admin.user.user_controller",
            "user_controller",
            "AdminUserService",
            "get_user_page",
            [
                ("username", "alice"),
                ("deptId", "9007199254740993"),
                ("createTime", "2026-01-01T00:00:00"),
                ("createTime", "2026-02-01T00:00:00"),
            ],
            {
                "username": "alice",
                "dept_id": 9007199254740993,
                "create_time": (datetime(2026, 1, 1), datetime(2026, 2, 1)),
            },
        ),
        (
            "module_infra.controller.admin.config.config_data_controller",
            "config_data_controller",
            "ConfigDataService",
            "get_config_list_with_type_name",
            [
                ("name", "redis"),
                ("typeId", "9007199254740993"),
                ("createTime", "2026-01-01T00:00:00"),
                ("createTime", "2026-02-01T00:00:00"),
            ],
            {
                "name": "redis",
                "type_id": 9007199254740993,
                "create_time": (datetime(2026, 1, 1), datetime(2026, 2, 1)),
            },
        ),
        (
            "module_infra.controller.admin.config.config_type_controller",
            "config_type_controller",
            "ConfigTypeService",
            "get_config_type_page",
            [
                ("code", "runtime"),
                ("createTime", "2026-01-01T00:00:00"),
                ("createTime", "2026-02-01T00:00:00"),
            ],
            {"code": "runtime", "create_time": (datetime(2026, 1, 1), datetime(2026, 2, 1))},
        ),
        (
            "module_infra.controller.admin.job.job_log_controller",
            "job_log_controller",
            "JobLogService",
            "get_job_log_page",
            [
                ("jobId", "9007199254740993"),
                ("handlerName", "cleanup"),
                ("beginTime", "2026-01-01T00:00:00"),
            ],
            {
                "job_id": 9007199254740993,
                "handler_name": "cleanup",
                "begin_time": datetime(2026, 1, 1),
            },
        ),
        (
            "module_infra.controller.admin.mq.mq_log_controller",
            "mq_log_controller",
            "MqLogService",
            "get_log_page",
            [
                ("messageId", "message-1"),
                ("consumer", "worker"),
                ("beginTime", "2026-01-01T00:00:00"),
            ],
            {"message_id": "message-1", "consumer": "worker", "begin_time": datetime(2026, 1, 1)},
        ),
    ],
    ids=["user", "config-data", "config-type", "job-log", "mq-log"],
)
async def test_export_query_preserves_repeated_fields_filters_and_fetch_limit(
    module_name, router_name, service_name, method_name, filters, expected
):
    controller = importlib.import_module(module_name)
    router = getattr(controller, router_name)
    export_route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path.endswith("/export-excel")
    )
    request_type = get_type_hints(export_route.endpoint)["page_req_vo"]
    response_type = getattr(controller, request_type.__name__.replace("ExportReqVO", "RespVO"))
    selected_fields = list(ExcelSchema(response_type).export_columns())[:2][::-1]
    rows = [] if method_name == "get_config_list_with_type_name" else PageResult(items=[], total=0)
    query = AsyncMock(return_value=rows)
    service = SimpleNamespace(**{method_name: query})
    writer = ExcelWriter(
        ExcelSettings.model_validate(
            {**ConfigFactory.values()["config"]["models"]["excel"], "max_export_rows": 11}
        ),
        ConfigFactory.build(PageSettings, "page", fetch_all_max_rows=7),
    )
    writer.write = AsyncMock(wraps=writer.write)
    dependencies = {
        getattr(controller, service_name): service,
        ExcelWriter: writer,
        FileResult: FileResult(ConfigFactory.build(ResponseSettings, "response")),
    }
    if controller is user_module:
        dependencies[user_module.DeptService] = SimpleNamespace(
            get_dept_map=AsyncMock(return_value={})
        )
        dependencies[user_module.PostInfoProviderAdapter] = SimpleNamespace(
            names=AsyncMock(return_value={})
        )
    app = FastAPI()
    app.state.application_context = SimpleNamespace(
        container=SimpleNamespace(get=dependencies.__getitem__)
    )
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"{router.prefix}/export-excel",
            params=[*(("fields", field) for field in selected_fields), ("pageSize", "3"), *filters],
        )

    assert response.status_code == 200, response.text
    query.assert_awaited_once()
    request = query.call_args.args[0]
    assert request.fields == selected_fields
    assert request.page_size == 3
    assert request.fetch_all is True and request.fetch_all_max_rows == 7
    for field, value in expected.items():
        assert getattr(request, field) == value
    assert writer.write.call_args.args[1] is response_type
    assert writer.write.call_args.kwargs["fields"] == selected_fields
    workbook = load_workbook(BytesIO(response.content), read_only=True)
    try:
        assert next(workbook.active.values) == tuple(
            column.title
            for column in ExcelSchema(response_type).export_columns(selected_fields).values()
        )
    finally:
        workbook.close()


async def test_user_template_round_trip_needs_no_excel_business_providers():
    settings = ExcelSettings.model_validate(ConfigFactory.values()["config"]["models"]["excel"])
    service = SimpleNamespace(
        import_user_list=AsyncMock(
            return_value=UserImportRespVO(
                create_usernames=["dushan1", "dushan2"], update_usernames=[], failure_usernames={}
            )
        )
    )
    dependencies = {
        ExcelWriter: ExcelWriter(settings, ConfigFactory.build(PageSettings, "page")),
        ExcelReader: ExcelReader(settings),
        FileResult: FileResult(ConfigFactory.build(ResponseSettings, "response")),
        user_module.AdminUserService: service,
    }
    app = FastAPI()
    app.state.application_context = SimpleNamespace(
        container=SimpleNamespace(get=dependencies.__getitem__)
    )
    app.include_router(user_module.user_controller)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        template = await client.get("/user/get-import-template")
        assert template.status_code == 200
        imported = await client.post(
            "/user/import",
            files={
                "file": (
                    "users.xlsx",
                    template.content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"updateSupport": "true"},
        )

    assert imported.status_code == 200, imported.text
    assert imported.json()["data"]["createUsernames"] == ["dushan1", "dushan2"]
    service.import_user_list.assert_awaited_once()
    users, update_support = service.import_user_list.call_args.args
    assert [user.username for user in users] == ["dushan1", "dushan2"]
    assert [user.status for user in users] == [1, 0]
    assert update_support is True
