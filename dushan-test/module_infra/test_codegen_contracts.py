import ast
from pathlib import PurePosixPath

import pytest

from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.util.codegen.codegen_builder_utils import CodegenBuilderUtils
from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils


@pytest.mark.parametrize(
    "class_name,file_name",
    [
        ("DictData", "dict_data"),
        ("DictDataDO", "dict_data_do"),
        ("DictDataPageReqVO", "dict_data_page_req_vo"),
        ("OAuth2", "oauth2"),
        ("OAuth2DO", "oauth2_do"),
        ("OAuth2Client", "oauth2_client"),
        ("OAuth2ClientListReqVO", "oauth2_client_list_req_vo"),
        ("HTTPServer", "http_server"),
        ("HTTP", "http"),
        ("HTTPDO", "http_do"),
        ("UserID", "user_id"),
        ("UserIDDO", "user_id_do"),
    ],
)
def test_codegen_class_name_to_file_name(class_name, file_name):
    assert CodegenBuilderUtils.to_class_file_name(class_name) == file_name


@pytest.mark.parametrize("frontend", [0, 1])
@pytest.mark.parametrize("template", [1, 2, 15])
@pytest.mark.parametrize(
    "class_name,class_file_name",
    [("DictData", "dict_data"), ("OAuth2", "oauth2"), ("HTTP", "http"), ("UserID", "user_id")],
)
def test_native_codegen_variants_keep_types_and_safe_metadata(
    template, frontend, class_name, class_file_name
):
    table = CodegenTableDO(
        id=1,
        table_name="sample_record",
        module_name="sample",
        business_name="record",
        class_name=class_name,
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
                type_metadata_synced=True,
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
            class_name="ChildItem",
            table_comment="Child",
            class_comment="Child",
        )
        foreign = CodegenColumnDO(
            type_metadata_synced=True,
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
    output = CodegenEngineUtils().generate(table, columns, sub_tables=sub)
    assert len(output) >= 14
    names = [item["filePath"] for item in output]
    assert len(names) == len(set(names))
    python_classes = {}
    python_routers = {}
    python_imports = []
    for item in output:
        assert not item["filePath"].startswith("/") and ".." not in item["filePath"].split("/")
        if item["filePath"].endswith(".py"):
            tree = ast.parse(item["code"])
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            assert len(classes) == 1, item["filePath"]
            assert (
                CodegenBuilderUtils.to_class_file_name(classes[0].name)
                == PurePosixPath(item["filePath"]).stem
            )
            module = item["filePath"].removesuffix(".py").replace("/", ".")
            python_classes[module] = classes[0].name
            python_routers[module] = {
                target.id
                for node in tree.body
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "APIRouter"
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            python_imports.extend(
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("module_sample.")
            )
            assert "dal.mysql" not in item["code"]
            assert "SecurityDependencies" not in item["code"]
    for node in python_imports:
        assert node.module in python_classes
        assert {name.name for name in node.names} <= {
            python_classes[node.module],
            *python_routers[node.module],
        }
    query_kind = "list" if template == 2 else "page"
    vo_directory = "module_sample/controller/admin/record/vo"
    if template == 15:
        vo_directory += f"/{class_file_name}"
    python_paths = {
        f"module_sample/dal/dataobject/record/{class_file_name}_do.py",
        f"module_sample/dal/mapper/record/{class_file_name}_mapper.py",
        f"module_sample/service/record/{class_file_name}_service.py",
        f"module_sample/service/record/{class_file_name}_service_impl.py",
        f"module_sample/controller/admin/record/{class_file_name}_controller.py",
        f"{vo_directory}/{class_file_name}_save_req_vo.py",
        f"{vo_directory}/{class_file_name}_resp_vo.py",
        f"{vo_directory}/{class_file_name}_{query_kind}_req_vo.py",
    }
    if template != 2:
        python_paths.add(f"{vo_directory}/{class_file_name}_export_req_vo.py")
    assert "frontend/api/sample/record/index.ts" in names
    assert "sql/record_table.sql" in names
    if template == 15:
        python_paths.update(
            {
                "module_sample/dal/dataobject/child/child_item_do.py",
                "module_sample/dal/mapper/child/child_item_mapper.py",
                "module_sample/controller/admin/record/child_item_controller.py",
                "module_sample/controller/admin/record/vo/child_item/child_item_resp_vo.py",
            }
        )
    assert {name for name in names if name.endswith(".py")} == python_paths
    model = next(
        item["code"] for item in output if item["filePath"].endswith(f"/{class_file_name}_do.py")
    )
    assert "TenantBaseDO" in model and "Computed(" in model and "Index(" in model
    request = next(
        item["code"]
        for item in output
        if item["filePath"].endswith(f"/{class_file_name}_save_req_vo.py")
    )
    assert "active_key:" not in request and "SnowflakeReferenceInput" in request
    controller = next(
        item["code"]
        for item in output
        if item["filePath"].endswith(f"/{class_file_name}_controller.py")
    )
    assert "from framework.common.schemas.request import IdListReqVO" in controller
    assert "from framework.starter_web.public import" in controller
    assert "from framework.starter_web.routing.route_policy import" not in controller
    mapper = next(
        item["code"]
        for item in output
        if item["filePath"].endswith(f"/{class_file_name}_mapper.py")
    )
    assert "from framework.starter_database.public import" in mapper
    assert "from framework.starter_di.public import" in mapper
    service_impl = next(
        item["code"]
        for item in output
        if item["filePath"].endswith(f"/{class_file_name}_service_impl.py")
    )
    assert "from framework.starter_database.public import" in service_impl
    assert "from framework.starter_di.public import" in service_impl
    assert f"record_mapper: {class_name}Mapper" in service_impl
    if template == 15:
        assert "child_mapper: ChildItemMapper" in service_impl
        assert "self.child_mapper.select_list_by_record_id" in service_impl
    service = next(
        item["code"]
        for item in output
        if item["filePath"].endswith(f"/{class_file_name}_service.py")
    )
    for code in (controller, mapper, service, service_impl):
        if template == 2:
            assert f"{class_name}PageReqVO" not in code
        else:
            assert (
                f"from {vo_directory.replace('/', '.')}.{class_file_name}_page_req_vo "
                f"import {class_name}PageReqVO"
            ) in code
    if template == 2:
        assert "await service.get_record_list()" in controller
        assert "async def get_record_list(self)" in service
        assert "await self.record_mapper.select_list()" in service_impl
        assert "async def select_list(self)" in mapper
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
    assert "params: { ids }, paramsSerializer: 'repeat'" in " ".join(api.split())
    assert "ids.join" not in api and "ids.split" not in controller
