from __future__ import annotations

from framework.starter_di.decorators.components import util

_DB_TYPE_TO_PYTHON_TYPE: dict[str, str] = {
    "bigint": "int",
    "int": "int",
    "integer": "int",
    "mediumint": "int",
    "smallint": "int",
    "tinyint": "int",
    "float": "float",
    "double": "float",
    "decimal": "Decimal",
    "numeric": "Decimal",
    "bit": "bool",
    "boolean": "bool",
    "char": "str",
    "varchar": "str",
    "text": "str",
    "tinytext": "str",
    "mediumtext": "str",
    "longtext": "str",
    "enum": "str",
    "set": "str",
    "json": "json",
    "date": "datetime",
    "datetime": "datetime",
    "timestamp": "datetime",
    "time": "datetime",
    "year": "int",
    "blob": "bytes",
    "tinyblob": "bytes",
    "mediumblob": "bytes",
    "longblob": "bytes",
    "binary": "bytes",
    "varbinary": "bytes",
}
_IGNORE_COLUMN_NAMES = {
    "id",
    "creator",
    "create_time",
    "updater",
    "update_time",
    "deleted",
    "tenant_id",
}
_DATETIME_SUFFIXES = ("_time", "_date", "_at")
_TEXTAREA_SUFFIXES = ("_content", "_desc", "_remark", "_memo", "_description")


@util()
class CodegenBuilder:
    """代码生成默认值推断工具"""

    @staticmethod
    def build_class_name(table_name: str) -> str:
        """表名 → 实体类名（去前缀 + 驼峰化）

        例: system_user → User, infra_codegen_table → CodegenTable
        """
        parts = table_name.split("_", 1)
        if len(parts) > 1:
            name = parts[1]
        else:
            name = table_name
        return CodegenBuilder.to_pascal_case(name)

    @staticmethod
    def build_module_name(table_name: str) -> str:
        """表名 → 模块名（取第一段）

        例: system_user → system, infra_codegen_table → infra
        """
        parts = table_name.split("_")
        return parts[0] if parts else table_name

    @staticmethod
    def build_business_name(table_name: str) -> str:
        """表名 → 业务名（取最后一段）

        例: system_user → user, infra_codegen_table → table
        """
        parts = table_name.split("_")
        return parts[-1] if parts else table_name

    @staticmethod
    def build_class_comment(table_comment: str) -> str:
        """表描述 → 类描述（去除常见后缀）"""
        if not table_comment:
            return ""
        for suffix in ("表", "信息表", "配置表", "数据表"):
            if table_comment.endswith(suffix):
                return table_comment[: -len(suffix)]
        return table_comment

    @staticmethod
    def map_field_type(data_type: str) -> str:
        """数据库类型 → Python 字段类型"""
        dt = data_type.lower().strip()
        return _DB_TYPE_TO_PYTHON_TYPE.get(dt, "str")

    @staticmethod
    def build_field_name(column_name: str) -> str:
        """字段名 → Python 属性名（保持蛇形命名）

        例: user_name → user_name, id → id
        """
        return column_name.lower().strip()

    @staticmethod
    def is_primary_key(column_key: str) -> bool:
        """判断是否主键"""
        return column_key == "PRI"

    @staticmethod
    def should_create_operation(column_name: str) -> bool:
        """判断是否参与新增操作"""
        return column_name.lower() not in _IGNORE_COLUMN_NAMES

    @staticmethod
    def should_update_operation(column_name: str) -> bool:
        """判断是否参与编辑操作"""
        return column_name.lower() not in _IGNORE_COLUMN_NAMES

    @staticmethod
    def should_list_operation_result(column_name: str) -> bool:
        """判断是否在列表中展示"""
        return column_name.lower() not in {"deleted", "tenant_id"}

    @staticmethod
    def build_html_type(column_name: str, data_type: str) -> str:
        """推断前端显示类型"""
        cn = column_name.lower()
        if any((cn.endswith(s) for s in _DATETIME_SUFFIXES)):
            return "datetime"
        if any((cn.endswith(s) for s in _TEXTAREA_SUFFIXES)):
            return "textarea"
        if data_type.lower() in ("text", "mediumtext", "longtext"):
            return "textarea"
        if "image" in cn or "avatar" in cn or "logo" in cn or ("icon" in cn):
            return "imageUpload"
        if "file" in cn or "attachment" in cn:
            return "fileUpload"
        return "input"

    @staticmethod
    def to_pascal_case(name: str) -> str:
        """下划线分隔转 PascalCase"""
        return "".join((word.capitalize() for word in name.split("_") if word))

    @staticmethod
    def to_camel_case(name: str) -> str:
        """下划线分隔转 camelCase"""
        parts = [p for p in name.split("_") if p]
        if not parts:
            return name
        return parts[0].lower() + "".join((word.capitalize() for word in parts[1:]))
