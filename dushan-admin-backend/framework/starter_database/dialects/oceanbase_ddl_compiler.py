from sqlalchemy import DefaultClause
from sqlalchemy.dialects.mysql.base import MySQLDDLCompiler

from framework.starter_database.model.empty_json_object import EmptyJsonObject


class OceanBaseDdlCompiler(MySQLDDLCompiler):
    """按 OceanBase JSON 列不支持数据库默认值的能力编译建表语句。"""

    def get_column_default_string(self, column) -> str | None:
        """空 JSON 对象由插入层提供，其他类型默认值继续使用原生规则。"""
        if isinstance(column.server_default, DefaultClause) and isinstance(
            column.server_default.arg, EmptyJsonObject
        ):
            return None
        return super().get_column_default_string(column)
