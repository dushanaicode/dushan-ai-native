from __future__ import annotations

import io
import os
import zipfile
from typing import Any

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from framework.starter_di.decorators.components import util
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.definitions.enums.codegen.codegen_front_type_enum import CodegenFrontTypeEnum
from module_infra.service.codegen.inner.inner_codegen_builder import CodegenBuilder

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_BACKEND_TEMPLATES = [
    "python/do.py.jinja2",
    "python/mapper.py.jinja2",
    "python/service.py.jinja2",
    "python/service_impl.py.jinja2",
    "python/controller.py.jinja2",
    "python/vo/page_req_vo.py.jinja2",
    "python/vo/save_req_vo.py.jinja2",
    "python/vo/resp_vo.py.jinja2",
]
_SUB_TABLE_TEMPLATES = ["python_sub/do.py.jinja2", "python_sub/mapper.py.jinja2"]
_FRONTEND_COMMON_TEMPLATES = ["vue/api/index.ts.jinja2", "vue/views/data.ts.jinja2"]
_FRONTEND_ELE_TEMPLATES = ["vue_ele/views/index.vue.jinja2", "vue_ele/views/form.vue.jinja2"]
_FRONTEND_ANTD_TEMPLATES = ["vue_antd/views/index.vue.jinja2", "vue_antd/views/form.vue.jinja2"]
_SQL_TEMPLATES = ["sql/table.sql.jinja2", "sql/menu.sql.jinja2"]


@util()
class CodegenEngine:
    """基于 Jinja2 的代码生成引擎

    当前实现使用固定的 Jinja2 模板生成代码骨架。
    TODO: 后续计划接入 AI 员工（如 LLM Agent），使其能够基于上下文
          自动生成更完善的业务实现代码（如 controller 中的 CRUD 逻辑、
          service 层的业务处理等），而不仅仅是生成空壳/pass。
    """

    def __init__(self):
        self._env: Environment | None = None

    def _get_env(self) -> Environment:
        """懒加载 Jinja2 环境"""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(_TEMPLATE_DIR),
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self._env.filters["pyrepr"] = repr
            self._env.filters["storage_type"] = self.storage_type
            self._env.filters["computed_type"] = self.computed_type
            self._env.filters["request_type"] = self.request_type
            self._env.filters["response_type"] = self.response_type
            self._env.filters["camel_case"] = CodegenBuilder.to_camel_case
            self._env.filters["pascal_case"] = CodegenBuilder.to_pascal_case
        return self._env

    def generate(
        self,
        table: CodegenTableDO,
        columns: list[CodegenColumnDO],
        sub_tables: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, str]]:
        """生成所有代码文件

        Args:
            table: 主表 DO
            columns: 主表列列表
            sub_tables: 子表信息列表（主子表模板专用）

        Returns:
            List[dict], 每个 dict 包含 'filePath' 和 'code'
        """
        context = self._build_context(table, columns, sub_tables)
        template_files = self._get_template_files(table.template_type, table.front_type)
        files = []
        for tmpl_path in template_files:
            template = self._get_env().get_template(tmpl_path)
            code = template.render(**context)
            output_path = self._build_output_path(tmpl_path, table)
            files.append({"filePath": output_path, "code": code})
        if sub_tables:
            for sub_info in sub_tables:
                sub_context = self._build_sub_table_context(table, sub_info)
                for tmpl_path in _SUB_TABLE_TEMPLATES:
                    template = self._get_env().get_template(tmpl_path)
                    code = template.render(**sub_context)
                    output_path = self._build_sub_output_path(tmpl_path, table, sub_info["table"])
                    files.append({"filePath": output_path, "code": code})
        return files

    def generate_zip(
        self,
        table: CodegenTableDO,
        columns: list[CodegenColumnDO],
        sub_tables: list[dict[str, Any]] | None = None,
    ) -> bytes:
        """生成代码并打包为 zip"""
        files = self.generate(table, columns, sub_tables=sub_tables)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                zf.writestr(file["filePath"], file["code"])
        return buffer.getvalue()

    def _build_context(
        self,
        table: CodegenTableDO,
        columns: list[CodegenColumnDO],
        sub_tables: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """构建模板上下文"""
        from module_infra.definitions.enums.codegen.codegen_template_type_enum import (
            CodegenTemplateTypeEnum,
        )

        self._validate_identifiers(table, columns)
        primary_columns = [c for c in columns if c.primary_key]
        normal_columns = [c for c in columns if not c.primary_key]
        logger.debug(
            f"【CodegenEngine】构建上下文: table={table.table_name}, 总列数={len(columns)}, 主键列={len(primary_columns)}, 普通列={len(normal_columns)}"
        )
        for c in columns:
            logger.debug(
                f"【CodegenEngine】列: {c.column_name}, primary_key={c.primary_key}, field_name={c.field_name}, field_type={c.field_type}"
            )
        create_columns = [
            c
            for c in columns
            if c.create_operation and (not c.primary_key) and c.computed_expression is None
        ]
        update_columns = [
            c
            for c in columns
            if c.update_operation and (not c.primary_key) and c.computed_expression is None
        ]
        list_columns = [c for c in columns if c.list_operation]
        list_result_columns = [c for c in columns if c.list_operation_result]
        is_tree = table.template_type == CodegenTemplateTypeEnum.TREE.value
        is_sub = table.template_type == CodegenTemplateTypeEnum.SUB.value
        tree_parent_column = None
        tree_name_column = None
        if is_tree:
            tree_parent_column_id = table.tree_parent_column_id
            tree_name_column_id = table.tree_name_column_id
            if tree_parent_column_id:
                tree_parent_column = next(
                    (c for c in columns if c.id == tree_parent_column_id), None
                )
            if tree_name_column_id:
                tree_name_column = next((c for c in columns if c.id == tree_name_column_id), None)
        return {
            "table": table,
            "tenant_aware": any(c.field_name == "tenant_id" and not c.nullable for c in columns),
            "columns": columns,
            "primary_columns": primary_columns,
            "normal_columns": normal_columns,
            "create_columns": create_columns,
            "update_columns": update_columns,
            "list_columns": list_columns,
            "list_result_columns": list_result_columns,
            "enable_export": table.enable_export,
            "module_name": table.module_name,
            "business_name": table.business_name,
            "class_name": table.class_name,
            "class_comment": table.class_comment or table.table_comment,
            "table_name": table.table_name,
            "author": table.author or "codegen",
            "package_name": f"module_{table.module_name}",
            "template_type": table.template_type,
            "is_tree": is_tree,
            "is_sub": is_sub,
            "tree_parent_column": tree_parent_column,
            "tree_name_column": tree_name_column,
            "sub_tables": sub_tables or [],
        }

    def _build_sub_table_context(
        self, master_table: CodegenTableDO, sub_info: dict[str, Any]
    ) -> dict[str, Any]:
        """构建子表模板上下文"""
        sub_table = sub_info["table"]
        sub_columns = sub_info["columns"]
        sub_join_column = sub_info.get("sub_join_column")
        sub_normal_columns = [
            c
            for c in sub_columns
            if not c.primary_key
            and c.field_name not in ["creator", "create_time", "updater", "update_time", "deleted"]
        ]
        sub_join_field_name = sub_join_column.field_name if sub_join_column else None
        return {
            "tenant_aware": any(
                c.field_name == "tenant_id" and not c.nullable for c in sub_columns
            ),
            "master_table": master_table,
            "master_module_name": master_table.module_name,
            "master_business_name": master_table.business_name,
            "master_class_name": master_table.class_name,
            "table": sub_table,
            "columns": sub_columns,
            "normal_columns": sub_normal_columns,
            "sub_join_column": sub_join_column,
            "sub_join_field_name": sub_join_field_name,
            "module_name": sub_table.module_name,
            "business_name": sub_table.business_name,
            "class_name": sub_table.class_name,
            "class_comment": sub_table.class_comment or sub_table.table_comment,
            "table_name": sub_table.table_name,
            "package_name": f"module_{sub_table.module_name}",
        }

    def _get_template_files(self, template_type: int, front_type: int = 0) -> list[str]:
        """根据模板类型和前端类型返回要渲染的模板文件列表"""
        templates = []
        templates.extend(_BACKEND_TEMPLATES)
        templates.extend(_FRONTEND_COMMON_TEMPLATES)
        if front_type == CodegenFrontTypeEnum.VUE3_VBEN5_ANTD.value:
            templates.extend(_FRONTEND_ANTD_TEMPLATES)
        else:
            templates.extend(_FRONTEND_ELE_TEMPLATES)
        templates.extend(_SQL_TEMPLATES)
        return templates

    def _build_output_path(self, tmpl_path: str, table: CodegenTableDO) -> str:
        """构建输出文件路径"""
        module_name = table.module_name
        business_name = table.business_name
        output = tmpl_path.replace(".jinja2", "")
        if output.startswith("python/"):
            sub = output.replace("python/", "", 1)
            if sub.startswith("vo/"):
                vo_file = sub.replace("vo/", "")
                from module_infra.definitions.enums.codegen.codegen_template_type_enum import (
                    CodegenTemplateTypeEnum,
                )

                if (
                    vo_file == "page_req_vo.py"
                    and table.template_type == CodegenTemplateTypeEnum.TREE.value
                ):
                    vo_file = "list_req_vo.py"
                return f"module_{module_name}/controller/admin/{business_name}/vo/{business_name}_{vo_file}"
            elif sub == "do.py":
                return f"module_{module_name}/dal/dataobject/{business_name}/{business_name}_do.py"
            elif sub == "mapper.py":
                return f"module_{module_name}/dal/mapper/{business_name}/{business_name}_mapper.py"
            elif sub == "service.py":
                return f"module_{module_name}/service/{business_name}/{business_name}_service.py"
            elif sub == "service_impl.py":
                return (
                    f"module_{module_name}/service/{business_name}/{business_name}_service_impl.py"
                )
            elif sub == "controller.py":
                return f"module_{module_name}/controller/admin/{business_name}/{business_name}_controller.py"
            else:
                return f"module_{module_name}/{sub}"
        for prefix in ("vue_ele/", "vue_antd/", "vue/"):
            if output.startswith(prefix):
                sub = output.replace(prefix, "", 1)
                if sub.startswith("api/"):
                    return f"frontend/api/{module_name}/{business_name}/{sub.replace('api/', '')}"
                elif sub.startswith("views/"):
                    return (
                        f"frontend/views/{module_name}/{business_name}/{sub.replace('views/', '')}"
                    )
                else:
                    return f"frontend/{sub}"
        if output.startswith("sql/"):
            return f"sql/{business_name}_{output.replace('sql/', '')}"
        return output

    def _build_sub_output_path(
        self, tmpl_path: str, master_table: CodegenTableDO, sub_table: CodegenTableDO
    ) -> str:
        """构建子表输出文件路径"""
        module_name = sub_table.module_name
        business_name = sub_table.business_name
        output = tmpl_path.replace(".jinja2", "")
        if output.startswith("python_sub/"):
            sub = output.replace("python_sub/", "", 1)
            if sub == "do.py":
                return f"module_{module_name}/dal/dataobject/{business_name}/{business_name}_do.py"
            elif sub == "mapper.py":
                return f"module_{module_name}/dal/mapper/{business_name}/{business_name}_mapper.py"
        return output

    @staticmethod
    def _validate_identifiers(table, columns):
        import keyword

        names = (
            table.module_name,
            table.business_name,
            table.class_name,
            *(column.field_name for column in columns),
        )
        if any((not name.isidentifier() or keyword.iskeyword(name) for name in names)):
            raise ValueError("生成的模块、业务、类和字段名称必须是 Python 标识符")
        if [column.field_name for column in columns if column.primary_key] != ["id"]:
            raise ValueError("Native 代码模板要求单一 id 主键")

    @staticmethod
    def request_type(column):
        if column.field_name == "parent_id":
            return "SnowflakeReferenceInput"
        if column.field_name.endswith("_id") and column.field_type == "int":
            return "SnowflakeIdInput"
        return {
            "int": "int",
            "str": "str",
            "bool": "bool",
            "datetime": "datetime",
            "json": "dict",
            "float": "float",
            "Decimal": "Decimal",
            "bytes": "bytes",
        }[column.field_type]

    @staticmethod
    def response_type(column):
        value = CodegenEngine.request_type(column)
        return {
            "SnowflakeIdInput": "SnowflakeIdStr",
            "SnowflakeReferenceInput": "SnowflakeCursorStr",
        }.get(value, value)

    @staticmethod
    def storage_type(column):
        return "dict" if column.field_type == "json" else column.field_type

    @staticmethod
    def computed_type(column):
        if column.field_type == "str":
            return f"String({column.column_size or 255})"
        if column.data_type in {"smallint", "tinyint"}:
            return "SmallInteger"
        return {
            "int": "BigInteger",
            "float": "Float",
            "Decimal": "Numeric(18,4)",
            "bytes": "LargeBinary",
            "bool": "Boolean",
            "datetime": "DateTime",
            "json": "JSON",
        }[column.field_type]
