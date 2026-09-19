import asyncio
import inspect
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from contextvars import Context, ContextVar
from typing import Literal

from loguru import logger

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_database.connection.data_source_registry import DataSourceRegistry
from framework.starter_database.context.database_context import DatabaseContext
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.model.model_policy import ModelPolicy
from framework.starter_database.session.managed_async_session import ManagedAsyncSession
from framework.starter_database.transaction.commit_action import CommitAction
from framework.starter_database.transaction.commit_result import CommitResult
from framework.starter_database.transaction.database_operation import DatabaseOperation
from framework.starter_database.transaction.transaction_frame import TransactionFrame


class TransactionManager:
    """单应用事务边界；Session 不能跨任务复用，失败的 REQUIRED 子操作使外层仅可回滚。"""

    def __init__(
        self, registry: DataSourceRegistry, context: DatabaseContext, policy: ModelPolicy
    ) -> None:
        self.registry, self.context, self.policy = registry, context, policy
        self._current: ContextVar[TransactionFrame | None] = ContextVar(
            f"transaction_{id(self)}", default=None
        )
        self.results = deque(maxlen=registry.settings.after_commit_result_limit)
        self._tasks: set[asyncio.Task] = set()
        self.task_runner = None
        self._operation = ContextVar(f"database_operation_admission_{id(self)}", default=None)
        self._operations: set[DatabaseOperation] = set()
        self._idle = asyncio.Event()
        self._idle.set()
        self._draining = False

    def _reserve_operation(self):
        self.registry.require_ready()
        parent = self._operation.get()
        if self._draining and (parent is None or not parent.active):
            raise DatabaseException(error_code=DatabaseErrorCodes.NOT_READY)
        operation = DatabaseOperation()
        self._operations.add(operation)
        self._idle.clear()
        return operation

    def _release_operation(self, operation):
        if operation.active:
            operation.active = False
            self._operations.remove(operation)
            if not self._operations:
                self._idle.set()

    @contextmanager
    def _activate_operation(self, operation):
        token = self._operation.set(operation)
        try:
            yield
        finally:
            self._operation.reset(token)

    @contextmanager
    def _operation_scope(self):
        operation = self._reserve_operation()
        try:
            with self._activate_operation(operation):
                yield
        finally:
            self._release_operation(operation)

    def in_current_operation(self) -> bool:
        operation = self._operation.get()
        return operation is not None and operation.active

    async def drain_operations(self):
        self._draining = True
        await self._idle.wait()

    def cancel_callbacks(self):
        for task in tuple(self._tasks):
            task.cancel("数据库启动未完成，取消待就绪回调")

    def current(self) -> TransactionFrame | None:
        frame = self._current.get()
        if frame is not None and (not frame.active or frame.owner is not asyncio.current_task()):
            raise DatabaseException(error_code=DatabaseErrorCodes.CONTEXT_MISMATCH)
        return frame

    def _source(self, source):
        execution = self.context.current()
        return (
            source if source is not None else (None if execution is None else execution.datasource)
        )

    def _session(self, entry, *, readonly):
        return ManagedAsyncSession(
            bind=entry.engine,
            expire_on_commit=False,
            close_resets_only=False,
            database_policy=self.policy,
            readonly=readonly,
            execution=self.context.current(),
        )

    @asynccontextmanager
    async def transaction(
        self,
        *,
        source=None,
        propagation: Literal["required", "requires_new", "nested"] = "required",
    ):
        with self._operation_scope(), DatabaseErrorTranslator.boundary():
            async with self._transaction(source=source, propagation=propagation) as session:
                yield session

    @asynccontextmanager
    async def _transaction(self, *, source, propagation):
        if propagation not in {"required", "requires_new", "nested"}:
            raise ValueError("未知事务传播策略")
        source = self._source(source)
        current = None if propagation == "requires_new" else self.current()
        if current is not None:
            if source is not None and source != current.source:
                raise ValueError("当前事务不能切换数据源；独立事务请显式使用 requires_new")
            if propagation == "nested":
                async with self._savepoint(current) as session:
                    yield session
            else:
                try:
                    yield current.session
                except BaseException:
                    current.rollback_only = True
                    raise
            return
        entry = self.registry.acquire(readonly=False, source=source)
        try:
            session = self._session(entry, readonly=False)
        except BaseException:
            entry.release()
            raise
        frame = TransactionFrame(session, entry.source.name, asyncio.current_task())
        token = self._current.set(frame)
        primary = None
        committed = False
        phase = "begin"
        try:
            await session.begin()
            phase = "execute"
            execution = self.context.current()
            if execution is not None:
                execution.written = True
            yield session
        except BaseException as error:
            primary = DatabaseErrorTranslator.translate(
                error, dialect=entry.engine.dialect, phase=phase
            )
        finally:
            frame.active = False
            self._current.reset(token)
            if primary is None and frame.rollback_only:
                primary = DatabaseException(error_code=DatabaseErrorCodes.ROLLBACK_ONLY)

            async def finish():
                nonlocal committed, primary
                errors = []
                with session.sync_session.boundary():
                    try:
                        if primary is None:
                            await session.commit()
                            committed = True
                        else:
                            await session.rollback()
                    except BaseException as error:
                        translated = DatabaseErrorTranslator.translate(
                            error,
                            dialect=entry.engine.dialect,
                            phase="commit" if primary is None else "rollback",
                        )
                        if primary is None:
                            primary = translated
                        else:
                            errors.append(translated)
                        try:
                            await session.rollback()
                        except BaseException as rollback_error:
                            errors.append(
                                DatabaseErrorTranslator.translate(
                                    rollback_error, dialect=entry.engine.dialect, phase="rollback"
                                )
                            )
                    try:
                        await self._close_session(session, entry)
                    except BaseException as error:
                        errors.append(
                            DatabaseErrorTranslator.translate(
                                error, dialect=entry.engine.dialect, phase="close"
                            )
                        )
                CleanupUtils.raise_collected_cleanup_errors("事务终结失败", errors)

            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                finish, "数据库事务终结"
            )
            errors = [] if error is None else [error]
            if committed:
                callback_error, callback_cancel = await CleanupUtils.run_cancellation_safe_cleanup(
                    lambda: self._after_commit(frame.callbacks), "数据库提交后动作"
                )
                cancellation = cancellation or callback_cancel
                if callback_error is not None:
                    errors.append(callback_error)
            if committed and errors and primary is None:
                primary = AfterCommitException()
            CleanupUtils.raise_collected_cleanup_errors(
                "数据库事务失败", errors, primary_error=primary, caller_cancellation=cancellation
            )

    @asynccontextmanager
    async def _savepoint(self, frame):
        savepoint = await frame.session.begin_nested()
        callback_index = len(frame.callbacks)
        primary = None
        try:
            yield frame.session
        except BaseException as error:
            primary = error
        finally:
            if primary is not None:
                del frame.callbacks[callback_index:]

            async def finish():
                with frame.session.sync_session.boundary():
                    if primary is None:
                        with DatabaseErrorTranslator.boundary(phase="commit"):
                            await savepoint.commit()
                    else:
                        with DatabaseErrorTranslator.boundary(phase="rollback"):
                            await savepoint.rollback()

            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                finish, "数据库保存点终结"
            )
            if error is not None:
                frame.rollback_only = True
            CleanupUtils.raise_collected_cleanup_errors(
                "保存点失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )

    @asynccontextmanager
    async def read_session(self, *, source=None, force_primary=False):
        with self._operation_scope(), DatabaseErrorTranslator.boundary():
            async with self._read_session(source=source, force_primary=force_primary) as session:
                yield session

    @asynccontextmanager
    async def _read_session(self, *, source, force_primary):
        source = self._source(source)
        frame = self.current()
        if frame is not None:
            if source is not None and source != frame.source:
                raise ValueError("事务内读取必须使用当前事务的数据源")
            try:
                yield frame.session
            except BaseException:
                frame.rollback_only = True
                raise
            return
        execution = self.context.current()
        use_replica = not force_primary and not (execution is not None and execution.written)
        entry = self.registry.acquire(readonly=use_replica, source=source)
        try:
            session = self._session(entry, readonly=True)
        except BaseException:
            entry.release()
            raise
        primary = None
        try:
            yield session
        except BaseException as error:
            primary = DatabaseErrorTranslator.translate(error, dialect=entry.engine.dialect)
        finally:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                lambda: self._close_session(session, entry), "数据库读取会话关闭"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "读取会话失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )

    @staticmethod
    async def _close_session(session, entry):
        errors = []
        try:
            with session.sync_session.boundary():
                try:
                    await session.close()
                except BaseException as error:
                    errors.append(
                        DatabaseErrorTranslator.translate(
                            error, dialect=entry.engine.dialect, phase="close"
                        )
                    )
                    try:
                        await session.invalidate()
                    except BaseException as invalidation_error:
                        errors.append(
                            DatabaseErrorTranslator.translate(
                                invalidation_error, dialect=entry.engine.dialect, phase="close"
                            )
                        )
        finally:
            session.sync_session.active = False
            entry.release()
        CleanupUtils.raise_collected_cleanup_errors("Session 关闭失败", errors)

    def after_commit(self, callback, *, required=True, name=None) -> None:
        """关键动作只允许登记在事务内；普通动作在无事务时直接派发。"""
        if (
            not callable(callback)
            or inspect.isgeneratorfunction(callback)
            or inspect.isasyncgenfunction(callback)
        ):
            raise TypeError("提交后动作必须是普通或异步可调用对象，不能是生成器")
        action = CommitAction(
            callback,
            getattr(callback, "__qualname__", type(callback).__qualname__)
            if name is None
            else name,
            required,
        )
        frame = self.current()
        if frame is None:
            if required:
                raise DatabaseException(error_code=DatabaseErrorCodes.TRANSACTION_REQUIRED)
            self._schedule(action)
        else:
            frame.callbacks.append(action)

    async def _after_commit(self, actions) -> None:
        errors = []
        for action in actions:
            try:
                if action.required:
                    await self._invoke(action)
                else:
                    self._schedule(action)
            except BaseException as error:
                errors.append(DatabaseErrorTranslator.translate(error, phase="commit"))
        CleanupUtils.raise_collected_cleanup_errors("数据已提交，但后置动作失败", errors)

    def _schedule(self, action):
        operation = self._reserve_operation()
        try:
            task = (
                self.task_runner.create_task(
                    self._invoke_reserved,
                    action,
                    operation,
                    name=f"database-after-commit:{action.name}",
                    continuation=True,
                )
                if self.task_runner is not None
                else asyncio.create_task(
                    self._invoke_reserved(action, operation),
                    context=Context(),
                    name=f"database-after-commit:{action.name}",
                )
            )
        except BaseException:
            self._release_operation(operation)
            raise
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(lambda _: self._release_operation(operation))

    async def _invoke_reserved(self, action, operation):
        try:
            with self._activate_operation(operation):
                await self._invoke(action)
        finally:
            self._release_operation(operation)

    async def _invoke(self, action):
        token = self._current.set(None)
        try:
            with self.context.scope():
                result = action.callback()
                if inspect.isgenerator(result):
                    result.close()
                    raise TypeError("提交后动作不能返回生成器")
                if inspect.isasyncgen(result):
                    await result.aclose()
                    raise TypeError("提交后动作不能返回异步生成器")
                if inspect.isawaitable(result):
                    await result
        except BaseException as error:
            self.results.append(CommitResult(action.name, False, type(error).__name__))
            if action.required or isinstance(error, asyncio.CancelledError):
                raise
            logger.warning("数据库提交后动作失败：{}，{}", action.name, type(error).__name__)
        else:
            self.results.append(CommitResult(action.name, True))
        finally:
            self._current.reset(token)

    async def drain_callbacks(self):
        while self._tasks:
            tasks = tuple(self._tasks)
            await asyncio.gather(*tasks, return_exceptions=True)
            # 全部任务已完成时 gather 可同步返回，不能依赖尚未调度的 done 回调清空集合。
            self._tasks.difference_update(tasks)
