import ast
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import get_args

import pytest

from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.util.codegen.codegen_builder_utils import CodegenBuilderUtils
from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils

TEMPORAL_TYPES = {
    "date": (date, "2026-10-05"),
    "time": (time, "13:14:15"),
    "datetime": (datetime, "2026-10-05T13:14:15"),
    "timestamp": (datetime, "2026-10-05T13:14:15"),
}


@pytest.mark.parametrize("data_type", TEMPORAL_TYPES)
def test_codegen_temporal_type_inference(data_type):
    expected_type, _ = TEMPORAL_TYPES[data_type]
    assert CodegenBuilderUtils.map_field_type(f" {data_type.upper()} ") == expected_type.__name__
    assert CodegenBuilderUtils.build_html_type("value", data_type) == "datetime"


@pytest.mark.parametrize("frontend", [0, 1])
@pytest.mark.parametrize("template", [1, 2, 15])
@pytest.mark.parametrize("condition", ["=", "BETWEEN"])
@pytest.mark.parametrize("nullable", [False, True])
def test_generated_temporal_models_preserve_types(
    frontend, template, condition, nullable, tmp_path
):
    suffix = f"{frontend}_{template}_{int(condition == 'BETWEEN')}_{int(nullable)}"
    table = CodegenTableDO(
        id=1,
        table_name=f"temporal_{suffix}",
        module_name=f"temporal_{suffix}",
        business_name="event",
        class_name=f"Temporal{suffix.replace('_', '')}",
        class_comment="日期与时间",
        table_comment="日期与时间",
        template_type=template,
        front_type=frontend,
        enable_export=False,
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
        )
    ]
    for data_type in TEMPORAL_TYPES:
        for computed in (False, True):
            name = f"{'computed' if computed else 'value'}_{data_type}"
            columns.append(
                CodegenColumnDO(
                    type_metadata_synced=True,
                    id=len(columns) + 1,
                    table_id=1,
                    column_name=name,
                    field_name=name,
                    column_comment=name,
                    field_type=CodegenBuilderUtils.map_field_type(data_type),
                    data_type=data_type,
                    primary_key=False,
                    nullable=nullable,
                    create_operation=True,
                    update_operation=True,
                    list_operation=not computed,
                    list_operation_condition=condition,
                    list_operation_result=True,
                    html_type=CodegenBuilderUtils.build_html_type(name, data_type),
                    computed_expression=f"value_{data_type}" if computed else None,
                    computed_persisted=False if computed else None,
                )
            )
    sub_tables = []
    if template == 15:
        foreign_key = CodegenColumnDO(
            type_metadata_synced=True,
            id=len(columns) + 1,
            table_id=2,
            column_name="event_id",
            field_name="event_id",
            column_comment="主表编号",
            field_type="int",
            data_type="bigint",
            primary_key=False,
            nullable=False,
        )
        sub_tables.append(
            {
                "table": CodegenTableDO(
                    id=2,
                    table_name=f"temporal_child_{suffix}",
                    module_name=table.module_name,
                    business_name="child",
                    class_name=f"Child{table.class_name}",
                    class_comment="子表日期与时间",
                ),
                "columns": [*columns, foreign_key],
                "sub_join_column": foreign_key,
                "sub_join_many": True,
            }
        )
    files = CodegenEngineUtils().generate(table, columns, sub_tables)
    target = tmp_path
    if artifact_root := os.environ.get("DUSHAN_CODEGEN_TEMPORAL_ARTIFACTS"):
        target = Path(artifact_root).resolve()
        assert target.is_relative_to((Path.cwd() / "Temp").resolve())

    models = {}
    for item in files:
        path = target / item["filePath"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["code"], encoding="utf-8", newline="\n")
        if path.suffix == ".py":
            ast.parse(item["code"])
            if path.stem.endswith(("_do", "_req_vo", "_resp_vo")):
                namespace = {"__name__": __name__}
                exec(compile(item["code"], str(path), "exec"), namespace)
                model = next(
                    value
                    for name, value in namespace.items()
                    if name.startswith((table.class_name, f"Child{table.class_name}"))
                )
                models[path.stem] = model

    class_file_name = CodegenBuilderUtils.to_class_file_name(table.class_name)
    save_model = models[f"{class_file_name}_save_req_vo"]
    query_kind = "list" if template == 2 else "page"
    query_model = models[f"{class_file_name}_{query_kind}_req_vo"]
    response_model = models[f"{class_file_name}_resp_vo"]
    payload = {f"value_{name}": text for name, (_, text) in TEMPORAL_TYPES.items()}
    request = save_model.model_validate(payload)
    query = query_model.model_validate(
        {
            name: [value, value] if condition == "BETWEEN" else value
            for name, value in payload.items()
        }
    )
    response = response_model.model_validate(
        {"id": 1, "create_time": datetime(2026, 10, 5), **payload}
        | {f"computed_{name}": text for name, (_, text) in TEMPORAL_TYPES.items()}
    )
    for data_type, (python_type, text) in TEMPORAL_TYPES.items():
        name = f"value_{data_type}"
        assert type(getattr(request, name)) is python_type
        assert type(getattr(response, name)) is python_type
        query_value = getattr(query, name)
        assert type(query_value[0] if condition == "BETWEEN" else query_value) is python_type
        assert response.to_response()[CodegenBuilderUtils.to_camel_case(name)] == text
        assert f"computed_{data_type}" not in save_model.model_fields
        if nullable:
            assert (
                save_model.model_validate({}).model_dump()[CodegenBuilderUtils.to_camel_case(name)]
                is None
            )
        for stem, model in models.items():
            if stem.endswith("_do"):
                for field_name in (name, f"computed_{data_type}"):
                    column = model.__table__.c[field_name]
                    assert column.type.python_type is python_type
                    annotation = get_args(model.__annotations__[field_name])[0]
                    assert annotation == (
                        python_type | None if nullable or column.computed else python_type
                    )

    schema = next(item["code"] for item in files if item["filePath"].endswith("/data.ts"))
    form_schema = schema.split("/** 搜索表单 schema */")[0].split("/** 表格列 */")[0]
    for data_type in TEMPORAL_TYPES:
        field = CodegenBuilderUtils.to_camel_case(f"value_{data_type}")
        block = form_schema.split(f"fieldName: '{field}'", 1)[1].split("    },", 1)[0]
        if data_type == "time":
            assert "component: 'TimePicker'" in block and "valueFormat: 'HH:mm:ss'" in block
        else:
            value_format = "YYYY-MM-DD" if data_type == "date" else "YYYY-MM-DD HH:mm:ss"
            assert "component: 'DatePicker'" in block
            assert f"valueFormat: '{value_format}'" in block
    if template != 2:
        search = schema.split("/** 搜索表单 schema */")[1].split("/** 表格列 */")[0]
        if condition == "BETWEEN":
            assert ("isRange: true" if frontend == 0 else "picker: 'time'") in search
            assert "type: 'daterange'" in search if frontend == 0 else "showTime: true" in search
        else:
            assert "component: 'TimePicker'" in search
    api = next(item["code"] for item in files if item["filePath"].endswith("/index.ts"))
    for data_type in TEMPORAL_TYPES:
        name = CodegenBuilderUtils.to_camel_case(f"value_{data_type}")
        assert f"{name}{'?' if nullable else ''}: {'null | ' if nullable else ''}string;" in api
