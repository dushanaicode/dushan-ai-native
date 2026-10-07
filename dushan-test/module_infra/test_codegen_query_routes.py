import importlib
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Response
from httpx import ASGITransport, AsyncClient

from fixtures.config_factory import ConfigFactory
from framework.common.page import PageResult, PageSettings
from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.public import ExcelWriter
from framework.starter_web.public import FileResult
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.util.codegen.codegen_builder_utils import CodegenBuilderUtils
from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")


@pytest.mark.parametrize("template", [1, 2, 15])
async def test_generated_query_routes_parse_filters_and_export_fields(template, module_package):
    table = CodegenTableDO(
        id=1,
        table_name=f"query_record_{template}",
        module_name=f"query_record_{template}",
        business_name="record",
        class_name=f"QueryRecord{template}",
        class_comment="查询记录",
        table_comment="查询记录",
        template_type=template,
        front_type=0,
        enable_export=True,
    )
    columns = [
        CodegenColumnDO(
            type_metadata_synced=True,
            id=1,
            table_id=1,
            column_name="id",
            field_name="id",
            field_type="int",
            data_type="bigint",
            primary_key=True,
            nullable=False,
        ),
        CodegenColumnDO(
            type_metadata_synced=True,
            id=2,
            table_id=1,
            column_name="event_time",
            field_name="event_time",
            column_comment="事件时间",
            field_type="datetime",
            data_type="datetime",
            primary_key=False,
            nullable=False,
            create_operation=True,
            update_operation=True,
            list_operation=True,
            list_operation_condition="BETWEEN",
            list_operation_result=True,
            html_type="datetime",
        ),
    ]
    package = f"module_{table.module_name}"
    generated = CodegenEngineUtils().generate(table, columns)
    module_package(
        package,
        files={
            item["filePath"].removeprefix(f"{package}/"): item["code"]
            for item in generated
            if item["filePath"].endswith(".py")
        },
    )
    for item in generated:
        if item["filePath"].endswith(".py"):
            importlib.import_module(item["filePath"].removesuffix(".py").replace("/", "."))
    class_file_name = CodegenBuilderUtils.to_class_file_name(table.class_name)
    controller = importlib.import_module(
        f"{package}.controller.admin.record.{class_file_name}_controller"
    )
    service = SimpleNamespace(
        get_record_page=AsyncMock(return_value=PageResult.empty()),
        get_record_list=AsyncMock(return_value=[]),
    )
    writer = ExcelWriter(
        ExcelSettings.model_validate(
            {**ConfigFactory.values()["config"]["models"]["excel"], "max_export_rows": 50}
        ),
        ConfigFactory.build(PageSettings, "page", fetch_all_max_rows=100),
    )
    writer.write = AsyncMock(return_value=b"excel")
    files = SimpleNamespace(excel_stream=Mock(return_value=Response(b"excel")))
    instances = {
        getattr(controller, f"{table.class_name}Service"): service,
        ExcelWriter: writer,
        FileResult: files,
    }
    app = FastAPI()
    app.state.application_context = SimpleNamespace(
        container=SimpleNamespace(get=instances.__getitem__)
    )
    app.include_router(controller.record_controller)
    times = ["2026-10-01T00:00:00", "2026-10-05T00:00:00"]
    params = [("page", "1"), ("page", "2"), ("pageSize", "7")]
    params.extend(("eventTime", value) for value in times)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if template != 2:
            response = await client.get("/record/page", params=params)
            assert response.status_code == 200, response.text
            assert response.json()["data"] == {"items": [], "total": 0}
            query = service.get_record_page.await_args.args[0]
            assert query.page == 2 and query.page_size == 7
            assert query.event_time == [datetime.fromisoformat(value) for value in times]
            assert not query.fetch_all

        for fields in (None, ["event_time"], ["id", "event_time"]):
            export_params = [] if template == 2 else params.copy()
            export_params.extend(("fields", field) for field in fields or [])
            response = await client.get("/record/export-excel", params=export_params)
            assert response.status_code == 200, response.text
            assert response.content == b"excel"
            assert writer.write.await_args.kwargs["fields"] == fields
            if template == 2:
                service.get_record_list.assert_awaited()
                service.get_record_page.assert_not_awaited()
            else:
                query = service.get_record_page.await_args.args[0]
                assert query.page == 2 and query.page_size == 7
                assert query.event_time == [datetime.fromisoformat(value) for value in times]
                assert query.fields == fields
                assert query.fetch_all and query.fetch_all_max_rows == 50

        if template != 2:
            for path in ("/record/page", "/record/export-excel"):
                response = await client.get(path, params={"eventTime": "invalid"})
                assert response.status_code == 422, response.text
                assert response.json()["detail"][0]["loc"] == ["query", "eventTime", 0]
