import asyncio
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import Delete, Insert, Select, Update
from sqlalchemy.orm import Session
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.selectable import CompoundSelect

from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_result import ManagedResult


class ManagedSession(Session):
    """受管同步代理：归属任务固定，事务终结仅交给外层资源边界。"""

    def __init__(self, *args, database_policy, readonly, execution, **kwargs):
        self.owner = asyncio.current_task()
        self.active = True
        self.readonly = readonly
        self.execution = execution
        self._operation = ContextVar(f"database_operation_{id(self)}", default=None)
        self._boundary = ContextVar(f"database_boundary_{id(self)}", default=None)
        self._internal_parameters = ContextVar(f"database_parameters_{id(self)}", default=None)
        super().__init__(*args, **kwargs)
        database_policy.bind(self)

    def require_owner(self):
        task = asyncio.current_task()
        if not self.active or (task is not self.owner and self._boundary.get() is not task):
            raise DatabaseException(error_code=DatabaseErrorCodes.CONTEXT_MISMATCH)

    @contextmanager
    def boundary(self):
        token = self._boundary.set(asyncio.current_task())
        try:
            yield
        finally:
            self._boundary.reset(token)

    def _require_boundary(self):
        if self._boundary.get() is None or self._boundary.get() is not asyncio.current_task():
            raise DatabaseException(
                error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN,
                msg="事务提交、回滚和关闭由数据库上下文管理",
            )

    @contextmanager
    def operation(self):
        self.require_owner()
        token = self._operation.set(asyncio.current_task())
        try:
            yield
        finally:
            self._operation.reset(token)

    @property
    def bind(self):
        if self._operation.get() is None or self._operation.get() is not asyncio.current_task():
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        return self._engine_bind

    @bind.setter
    def bind(self, value):
        self._engine_bind = value

    def get_bind(self, *args, **kwargs):
        if self._operation.get() is None or self._operation.get() is not asyncio.current_task():
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        return super().get_bind(*args, **kwargs)

    @property
    def dialect_name(self):
        """只读方言名称，不向调用方暴露 Engine 或 Connection。"""
        self.require_owner()
        return self._engine_bind.dialect.name

    def connection(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    @staticmethod
    def validate_statement(statement, *, readonly=False):
        if not isinstance(statement, (Select, CompoundSelect, Insert, Update, Delete)):
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        for element in visitors.iterate(statement):
            if isinstance(element, TextClause):
                raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
            if readonly and (
                isinstance(element, (Insert, Update, Delete))
                or (isinstance(element, Select) and element._for_update_arg is not None)
            ):
                raise DatabaseException(
                    error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN, msg="只读会话不能写入或锁行"
                )

    def execute(self, statement, params=None, **kwargs):
        self.validate_statement(statement, readonly=self.readonly)
        if params is not None and self._internal_parameters.get() is not asyncio.current_task():
            valid = isinstance(params, Mapping) or (
                isinstance(statement, Insert)
                and isinstance(params, (list, tuple))
                and all(isinstance(row, Mapping) for row in params)
            )
            if not valid:
                raise ValueError("结构化执行参数须为 mapping；仅 INSERT 支持 mapping 列表")
        with self.operation(), DatabaseErrorTranslator.boundary(dialect=self._engine_bind.dialect):
            return ManagedResult(super().execute(statement, params, **kwargs))

    def scalar(self, statement, params=None, **kwargs):
        return self.execute(statement, params, **kwargs).scalar()

    def scalars(self, statement, params=None, **kwargs):
        return self.execute(statement, params, **kwargs).scalars()

    def get(self, *args, **kwargs):
        self.require_owner()
        token = self._internal_parameters.set(asyncio.current_task())
        try:
            return super().get(*args, **kwargs)
        finally:
            self._internal_parameters.reset(token)

    def refresh(self, *args, **kwargs):
        token = self._internal_parameters.set(asyncio.current_task())
        try:
            with self.operation():
                return super().refresh(*args, **kwargs)
        finally:
            self._internal_parameters.reset(token)

    def add(self, instance, *, _warn=True):
        self.require_owner()
        if self.readonly:
            raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
        return super().add(instance, _warn=_warn)

    def flush(self, *args, **kwargs):
        with (
            self.operation(),
            DatabaseErrorTranslator.boundary(dialect=self._engine_bind.dialect, phase="flush"),
        ):
            if self.readonly and (self.new or self.dirty or self.deleted):
                raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
            return super().flush(*args, **kwargs)

    def commit(self):
        self._require_boundary()
        with self.operation():
            return super().commit()

    def rollback(self):
        self._require_boundary()
        return super().rollback()

    def close(self):
        self._require_boundary()
        return super().close()

    def bulk_save_objects(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    def bulk_insert_mappings(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)

    def bulk_update_mappings(self, *args, **kwargs):
        raise DatabaseException(error_code=DatabaseErrorCodes.OPERATION_FORBIDDEN)
