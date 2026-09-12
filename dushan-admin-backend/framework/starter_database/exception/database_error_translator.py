import re
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.exc import (
    ArgumentError,
    CompileError,
    DBAPIError,
    IntegrityError,
    InvalidRequestError,
    ProgrammingError,
    SQLAlchemyError,
)
from sqlalchemy.exc import (
    TimeoutError as PoolTimeoutError,
)

from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException


class DatabaseErrorTranslator:
    """只按异常类型、SQLSTATE 和厂商数字码分类；绝不解析驱动消息或自动重试。"""

    _STATES = {
        "23505": "unique",
        "23503": "foreign_key",
        "23502": "not_null",
        "23514": "check",
        "40001": "serialization",
        "40P01": "deadlock",
        "57014": "statement_cancelled",
        "HYT00": "statement_timeout",
        "HYT01": "statement_timeout",
    }
    _MYSQL = {
        1022: "unique",
        1062: "unique",
        1451: "foreign_key",
        1452: "foreign_key",
        1048: "not_null",
        1364: "not_null",
        3819: "check",
        4025: "check",
        1213: "deadlock",
        1205: "statement_timeout",
        3024: "statement_timeout",
        1064: "programming",
        1054: "programming",
        1146: "programming",
        1040: "connection",
        2002: "connection",
        2003: "connection",
        2005: "connection",
        1045: "connection",
        2006: "connection",
        2013: "connection",
    }
    _SQLITE = {1555: "unique", 2067: "unique", 787: "foreign_key", 1299: "not_null", 275: "check"}
    _DM = {
        -6602: "unique",
        -6603: "foreign_key",
        -6607: "foreign_key",
        -6604: "check",
        -6606: "not_null",
        -2007: "programming",
        -2106: "programming",
        -6407: "statement_timeout",
        -6012: "connection",
    }
    _DIALECTS = {"mysql", "postgresql", "sqlite", "oceanbase", "opengauss", "kingbase", "dm"}
    _PHASES = {"execute", "flush", "begin", "commit", "rollback", "close", "connect", "migration"}
    _DRIVERS = {
        "sqlite3",
        "aiosqlite",
        "pymysql",
        "aiomysql",
        "asyncpg",
        "psycopg",
        "psycopg2",
        "dmPython",
        "dmAsync",
    }

    @classmethod
    def translate(cls, error: BaseException, *, dialect=None, phase="execute") -> BaseException:
        """返回安全数据库异常；非数据库异常（含取消）保持原样，异常组逐叶处理。"""
        if isinstance(error, DatabaseException):
            if phase in {"commit", "rollback", "close", "migration"}:
                error.context["phase"] = phase
                error.retryable = False
            # Engine 可能挂接 DBAPI 原因；这里不保留它或隐式上下文。
            if not isinstance(error.__cause__, (DatabaseException, BaseExceptionGroup)):
                error.__cause__ = None
            error.__context__ = None
            error.__suppress_context__ = True
            return error
        if isinstance(error, BaseExceptionGroup):
            children = [
                cls.translate(item, dialect=dialect, phase=phase) for item in error.exceptions
            ]
            if all(child is original for child, original in zip(children, error.exceptions)):
                return error
            return error.derive(children)
        if not isinstance(error, SQLAlchemyError) and not cls._is_driver_error(error):
            return error
        name = dialect if isinstance(dialect, str) else getattr(dialect, "name", None)
        name = name if name in cls._DIALECTS else None
        phase = phase if phase in cls._PHASES else "execute"
        original = error.orig if isinstance(error, DBAPIError) else error
        state, code = cls._codes(original)
        vendor_codes = (
            cls._MYSQL
            if name in {"mysql", "oceanbase"}
            else cls._SQLITE
            if name == "sqlite"
            else cls._DM
            if name == "dm"
            else {}
        )
        category = vendor_codes.get(code) or cls._STATES.get(state)
        if category is None and state is not None:
            category = {
                "23": "integrity",
                "42": "programming",
                "08": "connection",
                "28": "connection",
                "22": "data",
            }.get(state[:2])
        if category is None:
            if isinstance(error, PoolTimeoutError):
                category = "pool_timeout"
            elif isinstance(error, IntegrityError):
                category = "integrity"
            elif isinstance(
                error, (ProgrammingError, CompileError, ArgumentError, InvalidRequestError)
            ):
                category = "programming"
            elif isinstance(error, DBAPIError) and error.connection_invalidated:
                category = "connection"
            else:
                category = "database"
        context = {"category": category, "phase": phase}
        if name is not None:
            context["dialect"] = name
        if state is not None:
            context["sqlstate"] = state
        if code is not None:
            context["vendor_code"] = code
        safe = DatabaseException(error_code=cls._error_code(category), context=context)
        safe.retryable = category in {"deadlock", "serialization"} and phase in {
            "execute",
            "flush",
            "begin",
        }
        safe.__suppress_context__ = True
        return safe

    @classmethod
    def _codes(cls, original):
        state = None
        code = None
        # asyncpg 的 SQLAlchemy 适配层把 SQLSTATE 放在包装异常或其 cause 上。
        visited = set()
        while original is not None and id(original) not in visited:
            visited.add(id(original))
            for attribute in ("sqlstate", "pgcode"):
                value = getattr(original, attribute, None)
                if isinstance(value, str) and re.fullmatch(r"[0-9A-Z]{5}", value):
                    state = state or value
            for attribute in ("sqlite_errorcode", "errno", "code", "err_code"):
                value = getattr(original, attribute, None)
                if type(value) is int:
                    code = code if code is not None else value
            args = getattr(original, "args", ())
            if args and type(args[0]) is int and code is None:
                code = args[0]
            if args and code is None:
                value = getattr(args[0], "code", None)
                if type(value) is int:
                    code = value
            original = original.__cause__
        return state, code

    @classmethod
    def _is_driver_error(cls, error):
        return error is not None and any(
            base.__module__.split(".")[0] in cls._DRIVERS
            and base.__name__ in {"Error", "DatabaseError", "PostgresError"}
            for base in type(error).__mro__
        )

    @staticmethod
    def _error_code(category):
        return {
            "unique": DatabaseErrorCodes.UNIQUE_VIOLATION,
            "foreign_key": DatabaseErrorCodes.FOREIGN_KEY_VIOLATION,
            "not_null": DatabaseErrorCodes.NOT_NULL_VIOLATION,
            "check": DatabaseErrorCodes.CHECK_VIOLATION,
            "integrity": DatabaseErrorCodes.INTEGRITY_VIOLATION,
            "programming": DatabaseErrorCodes.PROGRAMMING_ERROR,
            "connection": DatabaseErrorCodes.CONNECTION_FAILED,
            "pool_timeout": DatabaseErrorCodes.POOL_TIMEOUT,
            "statement_timeout": DatabaseErrorCodes.STATEMENT_TIMEOUT,
            "statement_cancelled": DatabaseErrorCodes.STATEMENT_CANCELLED,
            "deadlock": DatabaseErrorCodes.DEADLOCK,
            "serialization": DatabaseErrorCodes.SERIALIZATION_FAILURE,
            "data": DatabaseErrorCodes.DATA_ERROR,
        }.get(category, DatabaseErrorCodes.ERROR)

    @classmethod
    @contextmanager
    def boundary(cls, *, dialect=None, phase="execute"):
        """截断驱动异常链；保留独立清理原因及非数据库异常。"""
        failure = None
        try:
            yield
        except BaseException as error:
            failure = cls.translate(error, dialect=dialect, phase=phase)
            if failure is error and not isinstance(error, DatabaseException):
                raise
        if failure is not None:
            try:
                raise failure from failure.__cause__
            finally:
                # contextlib.throw 的调用方仍可能处于异常处理中，须在 raise 后清除。
                failure.__context__ = None

    @classmethod
    def install(cls, engine) -> None:
        """给驱动失败附加安全诊断投影，不干预方言内部的异常类型判断。"""
        if not event.contains(engine, "handle_error", cls._handle_error):
            event.listen(engine, "handle_error", cls._handle_error, retval=True)

    @classmethod
    def _handle_error(cls, context):
        error = context.sqlalchemy_exception or context.original_exception
        safe = cls.translate(error, dialect=context.dialect)
        if safe is not error:
            error.__safe_diagnostic__ = safe.__safe_diagnostic__
