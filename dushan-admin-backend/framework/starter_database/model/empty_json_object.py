from sqlalchemy import JSON
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class EmptyJsonObject(FunctionElement):
    """用于 JSON 列数据库默认值的空对象表达式。"""

    type = JSON()
    inherit_cache = True

    @staticmethod
    def compile_default(element, compiler, **kwargs) -> str:
        """PostgreSQL 系列及达梦由 JSON 列将文本字面量转换为空对象。"""
        return "'{}'"

    @staticmethod
    def compile_mysql(element, compiler, **kwargs) -> str:
        """MySQL 系列使用支持 JSON 默认值的函数表达式。"""
        return "(JSON_OBJECT())"


compiles(EmptyJsonObject)(EmptyJsonObject.compile_default)
compiles(EmptyJsonObject, "mysql", "oceanbase")(EmptyJsonObject.compile_mysql)
