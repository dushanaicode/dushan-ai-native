from contextlib import contextmanager
from contextvars import ContextVar

from framework.starter_database.context.database_execution import DatabaseExecution
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException


class DatabaseContext:
    """请求值可供受管子任务使用，作用域退出即失效；Session 另行约束任务归属。"""

    def __init__(self) -> None:
        self._current: ContextVar[DatabaseExecution | None] = ContextVar(
            f"database_execution_{id(self)}", default=None
        )

    def current(self) -> DatabaseExecution | None:
        frame = self._current.get()
        if frame is not None and not frame.active:
            raise DatabaseException(error_code=DatabaseErrorCodes.CONTEXT_MISMATCH)
        return frame

    @contextmanager
    def scope(self, *, account_id=None, datasource=None, include_deleted=False):
        """为独立请求/任务创建值上下文，HTTP 流等受管子任务共享有效期。"""
        frame = DatabaseExecution(account_id, datasource, include_deleted)
        token = self._current.set(frame)
        try:
            yield frame
        finally:
            frame.active = False
            self._current.reset(token)

    @contextmanager
    def options(self, *, datasource=None, include_deleted=None, account_id=None):
        """临时修改当前操作选项，并把写入标记和生成 ID 合并回外层。"""
        parent = self.current()
        with self.scope(
            account_id=account_id
            if account_id is not None
            else (None if parent is None else parent.account_id),
            datasource=datasource
            if datasource is not None
            else (None if parent is None else parent.datasource),
            include_deleted=include_deleted
            if include_deleted is not None
            else (False if parent is None else parent.include_deleted),
        ) as frame:
            if parent is not None:
                frame.written = parent.written
            try:
                yield frame
            finally:
                if parent is not None:
                    parent.written |= frame.written
                    parent.generated_ids.extend(frame.generated_ids)
