import ast
import os
from pathlib import Path

import pytest

from module_infra.controller.admin.codegen.vo.codegen_table_resp_vo import CodegenTableRespVO
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.service.codegen.inner.inner_codegen_engine import CodegenEngine


@pytest.mark.parametrize("parent", [0, "0", None, 758589388660256768])
def test_codegen_parent_menu_response_keeps_root(parent):
    result = CodegenTableRespVO(
        id=1,
        data_source_config_id=2,
        table_name="qa_record",
        class_name="Record",
        parent_menu_id=parent,
    )
    assert result.parent_menu_id == (None if parent is None else str(parent))


@pytest.mark.parametrize("frontend", [0, 1])
@pytest.mark.parametrize("template", [1, 2, 15])
@pytest.mark.parametrize("export", [False, True])
def test_codegen_frontend_paths_and_rendered_contracts(frontend, template, export, tmp_path):
    module = f"qa{frontend}_{template}_{int(export)}"
    table = CodegenTableDO(
        id=1,
        table_name=f"{module}_record_item",
        module_name=module,
        business_name="record_item",
        class_name="RecordItem",
        table_comment="客户记录",
        class_comment='客户 "O\'Brien" <记录>',
        template_type=template,
        front_type=frontend,
        enable_export=export,
        tree_parent_column_id=4,
        tree_name_column_id=2,
        parent_menu_id=0,
    )
    columns = []
    for index, (name, field_type, data_type) in enumerate(
        [
            ("id", "int", "bigint"),
            ("name", "str", "varchar"),
            ("status", "int", "tinyint"),
            ("parent_id", "int", "bigint"),
            ("amount", "Decimal", "decimal"),
            ("event_time", "datetime", "datetime"),
            ("tenant_id", "str", "varchar"),
        ],
        1,
    ):
        columns.append(
            CodegenColumnDO(
                id=index,
                table_id=1,
                column_name=name,
                column_comment=f"{name} 的 '描述'",
                field_name=name,
                field_type=field_type,
                data_type=data_type,
                nullable=False,
                primary_key=name == "id",
                create_operation=name not in {"id", "tenant_id"},
                update_operation=name not in {"id", "tenant_id"},
                list_operation=name in {"name", "status", "event_time"},
                list_operation_condition="BETWEEN" if name == "event_time" and export else "=",
                list_operation_result=name != "tenant_id",
                dict_type="common_status" if name == "status" else None,
                html_type="radio"
                if name == "status"
                else "datetime"
                if name == "event_time"
                else "input",
                computed_expression=None,
                column_size=50,
            )
        )
    children = []
    if template == 15:
        child = CodegenTableDO(
            id=2,
            module_name=module,
            table_name=f"{module}_child_item",
            business_name="child_item",
            class_name="ChildItem",
            table_comment="子表",
            class_comment="子表",
        )
        children = [
            {
                "table": child,
                "columns": columns,
                "sub_join_column": columns[3],
                "sub_join_many": True,
            }
        ]
    files = CodegenEngine().generate(table, columns, sub_tables=children)
    paths = {item["filePath"] for item in files}
    assert f"frontend/views/{module}/record-item/modules/form.vue" in paths
    assert f"frontend/api/{module}/record-item/index.ts" in paths
    index = next(
        item["code"] for item in files if item["filePath"].endswith("/record-item/index.vue")
    )
    assert 'template #actions="{ row }"' in index
    assert " as number" not in index
    assert "CellOperation" not in index
    if template != 2:
        assert "page: page.currentPage" in index and "pageSize: page.pageSize" in index
        schema = next(item["code"] for item in files if item["filePath"].endswith("/data.ts"))
        search_schema = schema.split("export function useGridFormSchema")[1].split("/** 表格列 */")[
            0
        ]
        assert ("component: 'RangePicker'" in search_schema) == export
    if template == 15:
        assert "GridApi.setGridOptions({ data })" in index

    target = tmp_path
    if directory := os.environ.get("DUSHAN_CODEGEN_ARTIFACTS"):
        target = Path(directory).resolve()
        assert target.is_relative_to((Path.cwd() / "Temp").resolve())
    for item in files:
        path = (target / item["filePath"]).resolve()
        assert path.is_relative_to(target.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["code"], encoding="utf-8")
        if path.suffix == ".py":
            ast.parse(item["code"])
