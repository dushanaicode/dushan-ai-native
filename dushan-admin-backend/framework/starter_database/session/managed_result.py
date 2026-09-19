import asyncio
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy.engine import Result

from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException


class ManagedResult:
    """保留缓冲结果的查询接口，阻止从公开结果属性取得原始连接。"""

    _adapting: ContextVar[asyncio.Task | None] = ContextVar("database_result_adapter", default=None)

    def __init__(self, result: Result) -> None:
        self._result = result

    @classmethod
    @contextmanager
    def adaptation(cls):
        token = cls._adapting.set(asyncio.current_task())
        try:
            yield
        finally:
            cls._adapting.reset(token)

    def __getattr__(self, name):
        if name in {"connection", "context", "cursor", "raw"} and (
            self._adapting.get() is None or self._adapting.get() is not asyncio.current_task()
        ):
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        value = getattr(self._result, name)
        if not callable(value):
            return value

        def invoke(*args, **kwargs):
            result = value(*args, **kwargs)
            return ManagedResult(result) if isinstance(result, Result) else result

        return invoke

    def __iter__(self):
        return iter(self._result)

    def __next__(self):
        return next(self._result)

    def __enter__(self):
        self._result.__enter__()
        return self

    def __exit__(self, *args):
        return self._result.__exit__(*args)
