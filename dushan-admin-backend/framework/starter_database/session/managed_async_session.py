from sqlalchemy.ext.asyncio import AsyncSession

from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_result import ManagedResult
from framework.starter_database.session.managed_session import ManagedSession


class ManagedAsyncSession(AsyncSession):
    """SQLAlchemy 异步会话的受管入口，保留查询、ORM 与流式读取。"""

    sync_session_class = ManagedSession

    def __init__(self, *args, **kwargs):
        if kwargs.get("binds") or "sync_session_class" in kwargs:
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        super().__init__(*args, **kwargs)

    @property
    def sync_session(self):
        return self._managed_sync_session

    @sync_session.setter
    def sync_session(self, value):
        if not isinstance(value, ManagedSession) or "_managed_sync_session" in vars(self):
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        self._managed_sync_session = value

    @property
    def binds(self):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    @binds.setter
    def binds(self, value):
        if value:
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    @property
    def bind(self):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    @bind.setter
    def bind(self, value):
        pass

    def get_bind(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    async def connection(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    async def execute(self, *args, **kwargs):
        with ManagedResult.adaptation():
            return await super().execute(*args, **kwargs)

    async def stream(self, *args, **kwargs):
        with ManagedResult.adaptation():
            return await super().stream(*args, **kwargs)
