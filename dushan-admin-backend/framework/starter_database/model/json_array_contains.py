from sqlalchemy import Boolean, String, bindparam
from sqlalchemy.exc import UnsupportedCompilationError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class JsonArrayContains(FunctionElement):
    """判断 JSON 字符串数组是否包含完全相等的元素，值始终通过绑定参数传入。"""

    type = Boolean()
    inherit_cache = True

    def __init__(self, column, value: str):
        super().__init__(column, bindparam(None, value, type_=String()))

    @staticmethod
    def compile_default(element, compiler, **kwargs) -> str:
        """允许 ORM 离线解析查询结构，未支持的数据库方言仍直接报错。"""
        if compiler.dialect.name != "default":
            raise UnsupportedCompilationError(compiler, type(element))
        return JsonArrayContains.compile_postgresql(element, compiler, **kwargs)

    @staticmethod
    def compile_mysql(element, compiler, **kwargs) -> str:
        column, value = (compiler.process(arg, **kwargs) for arg in element.clauses)
        return f"JSON_CONTAINS({column}, JSON_QUOTE({value}))"

    @staticmethod
    def compile_postgresql(element, compiler, **kwargs) -> str:
        # openGauss 6.0 提供 json_build_array，构造后显式转成 JSONB。
        column, value = (compiler.process(arg, **kwargs) for arg in element.clauses)
        return (
            f"(CAST({column} AS JSONB) @> CAST(json_build_array(CAST({value} AS TEXT)) AS JSONB))"
        )

    @staticmethod
    def compile_sqlite(element, compiler, **kwargs) -> str:
        column, value = (compiler.process(arg, **kwargs) for arg in element.clauses)
        return (
            f"EXISTS (SELECT 1 FROM json_each({column}) "
            f"WHERE json_each.type = 'text' AND json_each.value = {value})"
        )

    @staticmethod
    def compile_dm(element, compiler, **kwargs) -> str:
        # JSON_OVERLAPS 只匹配顶层元素；SQL NULL 按不包含处理。
        column, value = (compiler.process(arg, **kwargs) for arg in element.clauses)
        return f"COALESCE(JSON_OVERLAPS({column}, TO_JSON({value})), 0)"


# ORM 的 get_final_froms() 在权限检查时使用无连接的 default 方言编译。
compiles(JsonArrayContains)(JsonArrayContains.compile_default)
compiles(JsonArrayContains, "mysql")(JsonArrayContains.compile_mysql)
compiles(JsonArrayContains, "postgresql", "kingbase")(JsonArrayContains.compile_postgresql)
compiles(JsonArrayContains, "sqlite")(JsonArrayContains.compile_sqlite)
compiles(JsonArrayContains, "dm")(JsonArrayContains.compile_dm)
