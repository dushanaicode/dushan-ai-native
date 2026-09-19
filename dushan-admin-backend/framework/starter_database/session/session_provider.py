import asyncio
from contextlib import asynccontextmanager, contextmanager
from contextvars import Context
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.data_source_registry import DataSourceRegistry
from framework.starter_database.connection.replication_status import ReplicationStatus
from framework.starter_database.context.database_context import DatabaseContext
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.model.model_policy import ModelPolicy
from framework.starter_database.spi.current_account_provider import CurrentAccountProvider
from framework.starter_database.spi.query_observer import QueryObserver
from framework.starter_database.spi.session_policy import SessionPolicy
from framework.starter_database.transaction.transaction_manager import TransactionManager
from framework.starter_di.decorators.components import framework


@framework
class SessionProvider:
    """应用持有的数据库入口；构造无 I/O，open/close 明确管理资源。

    使用 async with db.transaction() 提交写入，async with db.read_session()
    读取；请求/任务用 with db.scope() 保持写后主库和审计值。不可共享 Session。
    """

    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings
        self.context = DatabaseContext()
        self._registry = DataSourceRegistry(settings)
        self._transactions = TransactionManager(
            self._registry, self.context, ModelPolicy(settings, self.context)
        )
        self._replication = {}
        self._monitor: asyncio.Task | None = None
        self._closing: asyncio.Task | None = None
        self._monitor_error: BaseException | None = None
        self._monitor_state = "disabled" if not settings.health_check_enabled else "pending"
        self._monitor_started_at: str | None = None
        self._monitor_round_started_at: str | None = None
        self._monitor_checked_at: str | None = None
        self._monitor_finished_at: str | None = None
        self._monitor_stop_requested = False

    async def open(self) -> None:
        await self._registry.open()
        if self.settings.replication_check_enabled:
            await self.check_replication()
        if self.settings.health_check_enabled:
            self._monitor_state = "running"
            self._monitor_started_at = datetime.now(timezone.utc).isoformat()
            self._monitor = asyncio.create_task(
                self._monitor_health(), context=Context(), name="database-health"
            )
            self._monitor.add_done_callback(self._monitor_done)

    def scope(self, **options):
        return self.context.scope(**options)

    def options(self, **options):
        return self.context.options(**options)

    def transaction(self, *, source=None, propagation="required"):
        return self._transactions.transaction(source=source, propagation=propagation)

    def read_session(self, *, source=None, force_primary=False):
        return self._transactions.read_session(source=source, force_primary=force_primary)

    def after_commit(self, callback, *, required=True, name=None):
        self._transactions.after_commit(callback, required=required, name=name)

    def bind_task_runner(self, runner) -> None:
        self._transactions.task_runner = runner

    def bind_account_provider(self, provider: CurrentAccountProvider) -> None:
        self._transactions.policy.account_provider = provider

    @contextmanager
    def use_session_policy(self, policy: SessionPolicy):
        """装配阶段绑定记录策略；退出前宿主必须排空业务，已有会话保留其策略。"""
        policies = self._transactions.policy.session_policies
        if policy in policies:
            raise ValueError("Session 策略不能重复绑定")
        policies.append(policy)
        try:
            yield
        finally:
            policies.remove(policy)

    def bind_query_observer(self, observer: QueryObserver | None) -> None:
        """绑定或移除同步安全查询消费者；适用于现有和随后发布的数据源。"""
        self._registry.bind_query_observer(observer)

    def observe_queries(self, observer: QueryObserver):
        """为应用资源步骤提供独占、可撤销的查询观测绑定。"""
        return self._registry.observe_queries(observer)

    def next_id(self) -> int:
        """生成并按当前作用域记录 Snowflake ID；数据库自增策略不提供外部分配。"""
        self._registry.require_ready()
        ids = self._transactions.policy.ids
        if ids is None:
            raise ValueError("外部分配 ID 要求 snowflake 策略")
        identifier = ids.get_id()
        execution = self.context.current()
        if execution is not None:
            execution.generated_ids.append(identifier)
        return identifier

    async def replace_sources(self, sources, *, preflight=False) -> int:
        return await self._registry.replace_named(tuple(sources), preflight=preflight)

    @property
    def is_ready(self) -> bool:
        self._consume_monitor()
        return (
            self._closing is None
            and self._monitor_error is None
            and any(
                entry.source.role == "primary" and entry.healthy
                for entry in self._registry.entries.values()
            )
        )

    def get_metrics(self) -> dict:
        self._consume_monitor()
        return {
            **self._registry.metrics(),
            "replication": dict(self._replication),
            "after_commit": tuple(self._transactions.results),
            "monitor": {
                "state": self._monitor_state,
                "started_at": self._monitor_started_at,
                "round_started_at": self._monitor_round_started_at,
                "checked_at": self._monitor_checked_at,
                "finished_at": self._monitor_finished_at,
                "error_type": (
                    type(self._monitor_error).__name__ if self._monitor_error is not None else None
                ),
            },
        }

    async def check_health(self) -> dict[str, bool]:
        return await self._registry.check_health()

    async def check_replication(self) -> dict:
        self._registry.require_ready()
        result = {}
        for entry in tuple(self._registry.entries.values()):
            if entry.source.role != "replica" or entry.retired:
                continue
            entry.acquire()
            try:
                async with asyncio.timeout(self.settings.connect_timeout_seconds):
                    status = await ReplicationStatus.read(entry)
                healthy = (
                    status["running"]
                    and status["lag_seconds"] <= self.settings.max_replication_lag_seconds
                )
                result[entry.source.name] = {**status, "healthy": healthy}
                if self.settings.replication_check_enabled:
                    self._registry.set_replication_health(entry, healthy)
            except (DatabaseException, SQLAlchemyError, OSError, TimeoutError, ValueError) as error:
                result[entry.source.name] = {"healthy": False, "error_type": type(error).__name__}
                if self.settings.replication_check_enabled:
                    self._registry.set_replication_health(entry, False)
            finally:
                entry.release()
        self._replication = result
        return result

    @asynccontextmanager
    async def lifespan(self):
        primary = None
        try:
            await self.open()
            yield self
        except BaseException as error:
            primary = error
        finally:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                self.close, "数据库生命周期清理"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "数据库生命周期失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )

    def _consume_monitor(self) -> None:
        # readiness 可能在 done 回调调度前读取，不能留下一个事件循环轮次的假健康。
        if self._monitor is not None and self._monitor.done():
            self._monitor_done(self._monitor)

    def _monitor_done(self, task: asyncio.Task) -> None:
        if task is not self._monitor or self._monitor_finished_at is not None:
            return
        self._monitor_finished_at = datetime.now(timezone.utc).isoformat()
        if task.cancelled():
            error = (
                None if self._monitor_stop_requested else RuntimeError("数据库健康监控被意外取消")
            )
        else:
            error = task.exception()
            if error is None and not self._monitor_stop_requested:
                error = RuntimeError("数据库健康监控意外结束")
        self._monitor_error = error
        self._monitor_state = "stopped" if error is None else "failed"
        if error is not None:
            logger.error("数据库健康监控异常结束：{}", type(error).__name__)

    async def _monitor_health(self):
        while True:
            await asyncio.sleep(self.settings.health_check_interval_seconds)
            self._monitor_round_started_at = datetime.now(timezone.utc).isoformat()
            await self.check_health()
            if self.settings.replication_check_enabled:
                await self.check_replication()
            self._monitor_checked_at = datetime.now(timezone.utc).isoformat()

    async def close(self) -> None:
        if self._transactions.in_current_operation():
            raise RuntimeError("不能在自身数据库操作内等待关闭；请先退出事务/会话边界")
        if self._closing is None:
            self._closing = asyncio.create_task(self._close(), name="database-close")
        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            lambda: asyncio.shield(self._closing), "等待数据库关闭"
        )
        CleanupUtils.raise_collected_cleanup_errors(
            "数据库关闭失败", [] if error is None else [error], caller_cancellation=cancellation
        )

    async def _close(self):
        errors = []
        if self._monitor is not None:
            # 先消费已终止任务，避免关闭把之前的意外取消误识别为正常取消。
            self._consume_monitor()
            if not self._monitor.done():
                self._monitor_stop_requested = self._monitor.cancelling() == 0
                self._monitor.cancel()
            try:
                await self._monitor
            except BaseException:
                # 错误统一由终态消费记录，关闭时再聚合上报，避免重复加入。
                pass
            self._monitor_done(self._monitor)
            if self._monitor_error is not None:
                errors.append(self._monitor_error)
            self._monitor = None
        try:
            await self._transactions.drain_operations()
            await self._transactions.drain_callbacks()
        except BaseException as error:
            errors.append(error)
        try:
            await self._registry.close()
        except BaseException as error:
            errors.append(error)
        if errors:
            logger.error("数据库关闭发现 {} 项错误", len(errors))
        CleanupUtils.raise_collected_cleanup_errors("数据库资源关闭失败", errors)
