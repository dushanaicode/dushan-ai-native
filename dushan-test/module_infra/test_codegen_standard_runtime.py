import importlib
import io
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.page import PageSettings
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.public import DictDataProvider, ExcelWriter
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.public import FileResult, Result
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils


def _column(index, name, *, field_type="str", data_type="varchar", **options):
    values = dict(
        id=index,
        table_id=1,
        column_name=name,
        field_name=name,
        column_comment=name,
        field_type=field_type,
        data_type=data_type,
        column_size=64,
        primary_key=name == "id",
        nullable=name != "id",
        create_operation=name != "id",
        update_operation=name != "id",
        list_operation=False,
        list_operation_result=True,
        html_type="input",
    )
    values.update(options)
    return CodegenColumnDO(type_metadata_synced=True, **values)


def _generate_case(template, has_dictionary, module_package):
    module_name = f"standard_runtime_{template}_{int(has_dictionary)}"
    table = CodegenTableDO(
        id=1,
        table_name=f"{module_name}_record",
        module_name=module_name,
        business_name="record",
        class_name="RecordHeader",
        class_comment="运行记录",
        table_comment="运行记录",
        template_type=template,
        front_type=0,
        enable_export=True,
        tree_parent_column_id=8,
        tree_name_column_id=2,
    )
    columns = [
        _column(1, "id", field_type="int", data_type="bigint"),
        _column(2, "name", nullable=False),
        _column(3, "note"),
        _column(4, "status", dict_type="record_status" if has_dictionary else None),
        _column(5, "private_code", dict_type="private_dict", list_operation_result=False),
        _column(6, "initial_value", update_operation=False),
        _column(7, "revision_note", create_operation=False),
        _column(8, "parent_id", field_type="int", data_type="bigint"),
    ]
    children = []
    if template == 15:
        child = CodegenTableDO(
            id=2,
            table_name=f"{module_name}_line_item",
            module_name=module_name,
            business_name="line_item",
            class_name="RecordLineItem",
            class_comment="记录明细",
            table_comment="记录明细",
        )
        foreign = _column(12, "record_id", field_type="int", data_type="bigint", nullable=False)
        children = [
            {
                "table": child,
                "columns": [
                    _column(11, "id", field_type="int", data_type="bigint"),
                    foreign,
                    _column(13, "detail"),
                    _column(14, "payload", field_type="json", data_type="json"),
                ],
                "sub_join_column": foreign,
                "sub_join_many": True,
            }
        ]
    generated = CodegenEngineUtils().generate(table, columns, sub_tables=children)
    package = f"module_{module_name}"
    python_files = {
        item["filePath"]: item["code"] for item in generated if item["filePath"].endswith(".py")
    }
    module_package(
        package,
        files={path.removeprefix(f"{package}/"): code for path, code in python_files.items()},
    )
    modules = {
        path: importlib.import_module(path.removesuffix(".py").replace("/", "."))
        for path in python_files
    }

    def generated_class(filename, name):
        return getattr(
            next(module for path, module in modules.items() if path.endswith(filename)), name
        )

    domain = f"{package}/controller/admin/record"
    vo_directory = f"{domain}/vo" + ("/header" if children else "")
    assert f"{vo_directory}/record_header_save_req_vo.py" in python_files
    assert f"{vo_directory}/record_header_resp_vo.py" in python_files
    assert len([path for path in python_files if path.endswith("_controller.py")]) == 1 + len(
        children
    )
    if children:
        assert f"{domain}/record_line_item_controller.py" in python_files
        assert f"{domain}/vo/line_item/record_line_item_resp_vo.py" in python_files
        assert not any(
            path.startswith(f"{package}/controller/admin/line_item/") for path in python_files
        )
    else:
        assert all(
            path.count("/vo/") == 0 or "/" not in path.split("/vo/")[1] for path in python_files
        )
    controller_module = modules[f"{domain}/record_header_controller.py"]
    return SimpleNamespace(
        controller=controller_module.RecordHeaderController,
        router=controller_module.record_controller,
        request=generated_class("record_header_save_req_vo.py", "RecordHeaderSaveReqVO"),
        model=generated_class("record_header_do.py", "RecordHeaderDO"),
        mapper=generated_class("record_header_mapper.py", "RecordHeaderMapper")(),
        service_type=generated_class("record_header_service.py", "RecordHeaderService"),
        service=generated_class("record_header_service_impl.py", "RecordHeaderServiceImpl")(),
        child_model=generated_class("record_line_item_do.py", "RecordLineItemDO")
        if children
        else None,
        child_mapper=generated_class("record_line_item_mapper.py", "RecordLineItemMapper")()
        if children
        else None,
        child_response=generated_class("record_line_item_resp_vo.py", "RecordLineItemRespVO")
        if children
        else None,
        child_controller=generated_class(
            "record_line_item_controller.py", "RecordLineItemController"
        )
        if children
        else None,
    )


@pytest.mark.parametrize("template", [1, 2, 15], ids=["single", "tree", "master_detail"])
@pytest.mark.parametrize("has_dictionary", [False, True], ids=["plain_export", "dictionary_export"])
async def test_generated_modules_execute_writes_exports_and_typed_children(
    template, has_dictionary, module_package, tmp_path, monkeypatch
):
    case = _generate_case(template, has_dictionary, module_package)
    values = ConfigFactory.values()
    database_values = values["config"]["models"]["database"]
    url = f"sqlite+aiosqlite:///{(tmp_path / 'generated.sqlite').as_posix()}"
    database_values.update(
        enabled=True,
        health_check_enabled=False,
        slow_query_enabled=False,
        id_strategy="snowflake",
        snowflake_machine_id=23,
        sources=[dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)],
    )
    database = SessionProvider(DatabaseSettings.model_validate(database_values))
    schema = create_async_engine(url)
    pages = ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True)
    case.mapper.session_provider = database
    case.mapper.paginator = SqlPaginator(pages)
    case.service.record_mapper = case.mapper
    models = [case.model]
    if case.child_mapper is not None:
        models.append(case.child_model)
        case.child_mapper.session_provider = database
        case.child_mapper.paginator = SqlPaginator(pages)
        case.service.line_item_mapper = case.child_mapper
    instances = {
        case.service_type: case.service,
        SessionProvider: database,
        ExcelWriter: ExcelWriter(
            ExcelSettings.model_validate(values["config"]["models"]["excel"]), pages
        ),
        FileResult: FileResult(ResponseSettings.model_validate(values["response"])),
    }
    dictionary = SimpleNamespace(items=AsyncMock(return_value={"ready": "就绪"}))
    if has_dictionary:
        instances[DictDataProvider] = dictionary
    monkeypatch.setattr(ApplicationContext, "lookup", staticmethod(instances.__getitem__))
    signature = get_type_hints(case.controller.export)
    assert signature["return"] is StreamingResponse
    assert (DictDataProvider in signature.values()) is has_dictionary
    write_calls = []
    original_write = case.request.to_write_dict

    def capture_write(request, *, fields, exclude_unset=True):
        result = original_write(request, fields=fields, exclude_unset=exclude_unset)
        write_calls.append((set(fields), exclude_unset, result))
        return result

    monkeypatch.setattr(case.request, "to_write_dict", capture_write)
    app = FastAPI()
    app.state.application_context = SimpleNamespace(
        container=SimpleNamespace(get=instances.__getitem__)
    )
    app.include_router(case.router)
    try:
        async with schema.begin() as connection:
            for model in models:
                await connection.run_sync(model.__table__.create)
        async with database.lifespan():
            with database.scope(account_id="codegen-test"):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/record/create",
                        json={
                            "name": "原始记录",
                            "status": "ready",
                            "note": "保留备注",
                            "initialValue": "不可修改",
                            "revisionNote": "新增时不写",
                        },
                    )
                    assert response.status_code == 200, response.text
                    identifier = response.json()["data"]
                    assert isinstance(identifier, str) and int(identifier) > 0
                    row = await case.mapper.select_by_id(int(identifier))
                    assert row.name == "原始记录" and row.revision_note is None
                    expected_create_fields = {
                        "id",
                        "name",
                        "note",
                        "status",
                        "private_code",
                        "initial_value",
                        "parent_id",
                    }
                    assert write_calls[0][:2] == (expected_create_fields, False)
                    assert write_calls[0][2]["private_code"] is None
                    assert write_calls[0][2]["parent_id"] is None
                    response = await client.put(
                        "/record/update",
                        json={
                            "id": identifier,
                            "name": "更新记录",
                            "initialValue": "禁止覆盖",
                            "revisionNote": "修改时写入",
                        },
                    )
                    assert response.status_code == 200, response.text
                    row = await case.mapper.select_by_id(int(identifier))
                    assert (row.name, row.note, row.status) == ("更新记录", "保留备注", "ready")
                    assert (row.initial_value, row.revision_note) == ("不可修改", "修改时写入")
                    assert write_calls[1][1] is True
                    assert write_calls[1][2] == {
                        "id": int(identifier),
                        "name": "更新记录",
                        "revision_note": "修改时写入",
                    }
                    response = await client.put(
                        "/record/update", json={"id": identifier, "name": "更新记录", "note": None}
                    )
                    assert response.status_code == 200, response.text
                    assert (await case.mapper.select_by_id(int(identifier))).note is None
                    assert write_calls[2][2] == {
                        "id": int(identifier),
                        "name": "更新记录",
                        "note": None,
                    }
                    response = await client.get(
                        "/record/export-excel", params=[("fields", "name"), ("fields", "status")]
                    )
                    assert response.status_code == 200, response.text
                    assert response.headers["content-type"].startswith(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    workbook = load_workbook(
                        io.BytesIO(response.content), read_only=True, data_only=True
                    )
                    try:
                        assert list(workbook.active.values) == [
                            ("name", "status"),
                            ("更新记录", "就绪" if has_dictionary else "ready"),
                        ]
                    finally:
                        workbook.close()
                    if has_dictionary:
                        dictionary.items.assert_awaited_once_with("record_status")
                    else:
                        dictionary.items.assert_not_awaited()
                    if case.child_mapper is not None:
                        child = case.child_model(
                            record_id=int(identifier), detail="实际明细", payload={"quantity": 3}
                        )
                        await case.child_mapper.insert(child)
                        assert (
                            get_type_hints(case.child_controller.get_line_item)["return"]
                            == Result[list[case.child_response]]
                        )
                        response = await client.get(
                            "/record/line-item/list-by-record-id", params={"id": identifier}
                        )
                        assert response.status_code == 200, response.text
                        assert response.json()["data"] == [
                            {
                                "id": str(child.id),
                                "recordId": identifier,
                                "detail": "实际明细",
                                "payload": {"quantity": 3},
                            }
                        ]
    finally:
        await schema.dispose()
