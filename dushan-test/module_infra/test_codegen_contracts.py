import ast

import pytest

from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.service.codegen.inner.inner_codegen_engine import CodegenEngine


@pytest.mark.parametrize("template,frontend", [(1, 0), (2, 0), (15, 1)])
def test_native_codegen_variants_keep_types_and_safe_metadata(template, frontend):
    table = CodegenTableDO(
        id=1,
        table_name="sample_record",
        module_name="sample",
        business_name="record",
        class_name="Record",
        table_comment='Text "quoted"',
        class_comment='Text "quoted"',
        author="test",
        template_type=template,
        front_type=frontend,
        enable_export=True,
        tree_parent_column_id=3,
        tree_name_column_id=2,
        parent_menu_id=0,
    )
    columns = []
    for index, (name, field_type, data_type) in enumerate(
        [
            ("id", "int", "bigint"),
            ("name", "str", "varchar"),
            ("parent_id", "int", "bigint"),
            ("tenant_id", "str", "varchar"),
            ("active_key", "int", "smallint"),
        ],
        1,
    ):
        columns.append(
            CodegenColumnDO(
                id=index,
                table_id=1,
                column_name=name,
                field_name=name,
                column_comment='A "description"',
                field_type=field_type,
                data_type=data_type,
                column_size=50,
                primary_key=name == "id",
                nullable=name == "active_key",
                create_operation=name not in {"id", "tenant_id"},
                update_operation=name not in {"id", "tenant_id"},
                list_operation=False,
                list_operation_result=True,
                dict_type=None,
                html_type="input",
                computed_expression="CASE WHEN deleted=0 THEN 1 ELSE NULL END"
                if name == "active_key"
                else None,
                computed_persisted=False if name == "active_key" else None,
            )
        )
    sub = []
    if template == 15:
        child = CodegenTableDO(
            id=2,
            table_name="sample_child",
            module_name="sample",
            business_name="child",
            class_name="Child",
            table_comment="Child",
            class_comment="Child",
        )
        foreign = CodegenColumnDO(
            id=11,
            table_id=2,
            column_name="record_id",
            field_name="record_id",
            column_comment="Record",
            field_type="int",
            data_type="bigint",
            nullable=False,
            primary_key=False,
            computed_expression=None,
        )
        sub = [
            {
                "table": child,
                "columns": [columns[0], foreign, columns[3]],
                "sub_join_column": foreign,
                "sub_join_many": True,
            }
        ]
    output = CodegenEngine().generate(table, columns, sub_tables=sub)
    assert len(output) >= 14
    names = [item["filePath"] for item in output]
    assert len(names) == len(set(names))
    for item in output:
        assert not item["filePath"].startswith("/") and ".." not in item["filePath"].split("/")
        if item["filePath"].endswith(".py"):
            ast.parse(item["code"])
            assert "dal.mysql" not in item["code"]
            assert "SecurityDependencies" not in item["code"]
    model = next(item["code"] for item in output if item["filePath"].endswith("record_do.py"))
    assert "TenantBaseDO" in model and "Computed(" in model and "Index(" in model
    request = next(
        item["code"] for item in output if item["filePath"].endswith("record_save_req_vo.py")
    )
    assert "active_key:" not in request and "SnowflakeReferenceInput" in request
    controller = next(
        item["code"] for item in output if item["filePath"].endswith("record_controller.py")
    )
    assert "from framework.common.schemas.request.id_list_req_vo import IdListReqVO" in controller
    tree = ast.parse(controller)
    batch = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "delete_list"
    )
    assert ast.unparse(batch.args.args[0].annotation) == "IdListReqVO"
    assert ast.unparse(batch.args.defaults[0]) == "Query()"
    assert "service.delete_record_batch(req_vo.ids)" in ast.unparse(batch)
    api = next(
        item["code"]
        for item in output
        if "/api/" in item["filePath"] and item["filePath"].endswith(".ts")
    )
    assert "params: { ids }, paramsSerializer: 'repeat'" in api
    assert "ids.join" not in api and "ids.split" not in controller
