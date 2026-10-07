import asyncio
import json

import dmPython
from dmSQLAlchemy.dmasync import DMDialectAsync_dmasync
from sqlalchemy import types as sqltypes
from sqlalchemy.util import await_only

from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.starter_database.ddl.dm_ddl_compiler import DmDdlCompiler
from framework.starter_database.dialects.dm_async_dbapi import DmAsyncDbapi
from framework.starter_database.dialects.dm_statement_compiler import DmStatementCompiler


class DmAsyncDialect(DMDialectAsync_dmasync):
    """沿用原厂 DM SQL 语法，连接适配通过独立 dm+dushan_async 入口发布。"""

    supports_statement_cache = True
    ddl_compiler = DmDdlCompiler
    statement_compiler = DmStatementCompiler
    # DM 的标量 INTO 不能承接多行 UPDATE/DELETE，ORM 应使用标准的同步策略。
    update_returning = False
    delete_returning = False
    # ORM 的 auto 默认值策略依赖批量 RETURNING；DM 不能返回虚拟列。
    insert_executemany_returning = False
    insert_executemany_returning_sort_by_parameter_order = False
    colspecs = {**DMDialectAsync_dmasync.colspecs, sqltypes.JSON: sqltypes.JSON}

    @staticmethod
    def _json_serializer(value):
        """显式编码 Unicode JSON，避免 DPI 把补充平面字符转换为无效 UTF-8。"""
        return json.dumps(value, ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _json_deserializer(value):
        return json.loads(value)

    @classmethod
    def get_async_dialect_cls(cls, url):
        return cls

    @classmethod
    def import_dbapi(cls):
        return DmAsyncDbapi(dmPython)

    def connect(self, *args, **kwargs):
        """固定 DPI 客户端为 UTF-8，避免继承 Windows 本机代码页。"""
        kwargs["local_code"] = dmPython.PG_UTF8
        return super().connect(*args, **kwargs)

    def do_ping(self, dbapi_connection):
        """原厂游标返回 awaitable；探活必须等待真实查询，不能仅创建协程。"""
        cursor = dbapi_connection.cursor()
        try:
            await_only(cursor.execute("SELECT 1"))
            return True
        finally:
            cursor.close()

    def do_execute(self, cursor, statement, parameters, context=None):
        """原厂 RETURNING 分支直接调用同步 DPI；在异步连接中交由线程完成。"""
        if (
            context is None
            or not context.out_parameters
            or not (context.isinsert or context.isupdate or context.isdelete)
        ):
            return super().do_execute(cursor, statement, parameters, context)
        positions, bound = self.resort_output_params(parameters, context)
        values = await_only(
            AsyncioUtils.run_cancellation_shielded(
                asyncio.to_thread(cursor._cursor.raw.execute, statement, bound)
            )
        )
        for index, position in enumerate(positions):
            # NULL 输出仍代表一条返回记录，不能用 [None] 判断零行。
            context.out_parameters[f"ret_{index}"] = (
                [] if cursor.rowcount == 0 else values[position]
            )
