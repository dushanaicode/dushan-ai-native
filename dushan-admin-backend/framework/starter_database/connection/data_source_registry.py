import asyncio
import random
from contextlib import contextmanager
from contextvars import Context
from inspect import isawaitable, iscoroutine

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.data_source_settings import DataSourceSettings
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.connection_factory import ConnectionFactory
from framework.starter_database.connection.engine_entry import EngineEntry
from framework.starter_database.connection.query_observation import QueryObservation
from framework.starter_database.connection.slow_query_listener import SlowQueryListener
from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.spi.query_observer import QueryObserver


class DataSourceRegistry:
    """应用独占的引擎集合：候选先探活、一次发布、旧租约归还后退休。"""

    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings
        self.entries: dict[str, EngineEntry] = {}
        self.revision = 0
        self._loop = None
        self._accepting = False
        self._lock = asyncio.Lock()
        self._retired: set[EngineEntry] = set()
        self._retirement_tasks: set[asyncio.Task] = set()
        self._retirement_errors: list[BaseException] = []
        self._listeners: dict[EngineEntry, SlowQueryListener] = {}
        self._round_robin = 0
        self._connectivity: dict[EngineEntry, bool] = {}
        self._replication_health: dict[EngineEntry, bool] = {}
        self._query_observer: QueryObserver | None = None
        self._observation_count = 0
        self._observation_failures = 0
        self._observation_error_type: str | None = None

    def bind_query_observer(self, observer: QueryObserver | None) -> None:
        self._query_observer = observer

    @contextmanager
    def observe_queries(self, observer: QueryObserver):
        """独占绑定一个资源期观察器，拒绝覆盖已有消费者，退出只撤销自身。"""
        if self._query_observer is not None:
            raise ValueError("查询观察器已有消费者，不能隐式覆盖")
        self._query_observer = observer
        try:
            yield
        finally:
            if self._query_observer is observer:
                self._query_observer = None

    def _observation_failed(self, error: BaseException) -> None:
        # 不保存异常对象/消息，避免消费者把原始 SQL 或参数反向带入诊断。
        self._observation_failures += 1
        self._observation_error_type = type(error).__name__

    def _observe(self, observation: QueryObservation, sampled: bool) -> None:
        self._observation_count += 1
        if (
            self.settings.slow_query_enabled
            and observation.elapsed_ms >= self.settings.slow_query_threshold_ms
        ):
            try:
                logger.warning(
                    "数据库慢查询：数据源 {}，操作 {}，耗时 {:.1f}ms，成功 {}，模板 {}，指纹 {}",
                    observation.source,
                    observation.operation,
                    observation.elapsed_ms,
                    observation.success,
                    observation.template,
                    observation.fingerprint,
                )
            except BaseException as error:
                self._observation_failed(error)
        if sampled and self._query_observer is not None:
            try:
                result = self._query_observer.observe(observation)
                if isawaitable(result):
                    if iscoroutine(result):
                        result.close()
                    raise TypeError("查询 observer 必须同步完成")
            except BaseException as error:
                self._observation_failed(error)

    def _update_health(self, entry: EngineEntry) -> None:
        entry.healthy = self._connectivity.get(entry, False) and (
            entry.source.role != "replica"
            or not self.settings.replication_check_enabled
            or self._replication_health.get(entry, False)
        )

    def set_replication_health(self, entry: EngineEntry, healthy: bool) -> None:
        self._replication_health[entry] = healthy
        self._update_health(entry)

    def require_ready(self) -> None:
        if not self._accepting or asyncio.get_running_loop() is not self._loop:
            raise DatabaseException(error_code=DatabaseErrorCodes.NOT_READY)

    async def open(self) -> None:
        if self._loop is not None or not self.settings.enabled:
            raise DatabaseException(error_code=DatabaseErrorCodes.NOT_READY)
        self._loop = asyncio.get_running_loop()
        logger.info("【DatabaseStarter 】开始创建连接池，验证连接与事务模式")
        self.entries = await self._stage(self.settings.sources)
        self.revision = 1
        self._accepting = True
        logger.info(
            "【DatabaseStarter 】连接池装配完成：{} 个数据源，通过连接探活 {} 个",
            len(self.entries),
            sum(self._connectivity.values()),
        )

    async def replace_named(
        self, sources: tuple[DataSourceSettings, ...], *, preflight=False
    ) -> int:
        """只替换 named 集合；主库和副本的连接配置需要重启应用。"""
        self.require_ready()
        if not self.settings.dynamic_enabled or any(source.role != "named" for source in sources):
            raise ValueError("动态替换要求启用 dynamic_enabled，且所有来源都是 named")
        async with self._lock:
            self.require_ready()
            definitions = (
                tuple(
                    entry.source for entry in self.entries.values() if entry.source.role != "named"
                )
                + sources
            )
            names = [source.name for source in definitions]
            if len(names) != len(set(names)):
                raise ValueError("动态数据源不能重名或覆盖静态源")
            if {source.name: source for source in definitions} == {
                name: entry.source for name, entry in self.entries.items()
            }:
                return self.revision
            candidates = await self._stage(definitions)
            if preflight:
                created = set(candidates.values()) - set(self.entries.values())
                await self._cleanup_entries(created)
                return self.revision
            previous = self.entries
            self.entries = candidates
            self.revision += 1
            retired = set(previous.values()) - set(candidates.values())
            for entry in retired:
                entry.retired = True
            self._retired.update(retired)
            if retired:
                task = asyncio.create_task(
                    self._dispose_entries(retired), context=Context(), name="database-retire"
                )
                self._retirement_tasks.add(task)
                task.add_done_callback(self._retirement_done)
            return self.revision

    async def _stage(self, definitions) -> dict[str, EngineEntry]:
        result = {}
        created: set[EngineEntry] = set()
        try:
            for source in definitions:
                previous = self.entries.get(source.name)
                if previous is not None and previous.source == source:
                    result[source.name] = previous
                    continue
                entry = EngineEntry(source, ConnectionFactory.create(source, self.settings))
                created.add(entry)
                url = entry.engine.url
                logger.debug(
                    "【DatabaseStarter 】数据源={} role={} driver={} host={} port={} database={}",
                    source.name,
                    source.role,
                    url.drivername,
                    url.host,
                    url.port,
                    url.database,
                )
                if self.settings.slow_query_enabled or self.settings.query_observation_enabled:
                    self._listeners[entry] = SlowQueryListener(
                        entry.engine,
                        source.name,
                        self.settings,
                        self._observe,
                        self._observation_failed,
                    )
                try:
                    async with asyncio.timeout(self.settings.connect_timeout_seconds):
                        await ConnectionFactory.probe(entry.engine)
                        await ConnectionFactory.validate_transaction_mode(entry.engine)
                    self._connectivity[entry] = True
                    logger.debug(
                        "【DatabaseStarter 】数据源 {} 连接与事务模式验证通过", source.name
                    )
                except (DatabaseException, SQLAlchemyError, OSError, TimeoutError) as error:
                    if source.role != "replica":
                        if isinstance(error, DatabaseException):
                            raise
                        if isinstance(error, SQLAlchemyError):
                            raise DatabaseErrorTranslator.translate(
                                error, dialect=entry.engine.dialect, phase="connect"
                            ) from None
                        raise DatabaseException(
                            error_code=DatabaseErrorCodes.CONNECTION_FAILED,
                            msg=f"数据源连接失败：{source.name}",
                        ) from None
                    self._connectivity[entry] = False
                    logger.warning("副本探活失败：{}，{}", source.name, type(error).__name__)
                self._update_health(entry)
                result[source.name] = entry
            return result
        except BaseException as primary:
            await self._cleanup_entries(created, primary=primary)
            raise

    def acquire(self, *, readonly: bool, source: str | None = None) -> EngineEntry:
        self.require_ready()
        if source is not None:
            if source not in self.entries:
                raise ValueError(f"数据源未注册：{source}")
            entry = self.entries[source]
            if not readonly and entry.source.role == "replica":
                raise ValueError("写事务不能使用 replica 数据源")
        else:
            candidates = (
                [
                    entry
                    for entry in self.entries.values()
                    if entry.source.role == "replica" and entry.healthy
                ]
                if readonly
                else []
            )
            entry = (
                self._select(candidates)
                if candidates
                else next(
                    entry for entry in self.entries.values() if entry.source.role == "primary"
                )
            )
        entry.acquire()
        return entry

    def _select(self, entries: list[EngineEntry]) -> EngineEntry:
        match self.settings.replica_strategy:
            case "random":
                return random.choice(entries)
            case "weighted":
                return random.choices(
                    entries, weights=[entry.source.weight for entry in entries], k=1
                )[0]
            case "least_connections":
                return min(entries, key=lambda entry: entry.leases)
            case "round_robin":
                entry = entries[self._round_robin % len(entries)]
                self._round_robin += 1
                return entry

    async def check_health(self) -> dict[str, bool]:
        self.require_ready()
        result = {}
        for entry in tuple(self.entries.values()):
            if entry.retired:
                continue
            entry.acquire()
            try:
                async with asyncio.timeout(self.settings.connect_timeout_seconds):
                    await ConnectionFactory.probe(entry.engine)
                self._connectivity[entry] = True
            except (DatabaseException, SQLAlchemyError, OSError, TimeoutError) as error:
                self._connectivity[entry] = False
                logger.warning("数据库探活失败：{}，{}", entry.source.name, type(error).__name__)
            finally:
                entry.release()
            self._update_health(entry)
            result[entry.source.name] = entry.healthy
        return result

    def metrics(self) -> dict:
        pools = {}
        for name, entry in self.entries.items():
            pool = entry.engine.pool
            pools[name] = {
                "role": entry.source.role,
                "healthy": entry.healthy,
                "connected": self._connectivity.get(entry, False),
                "replication_healthy": self._replication_health.get(entry),
                "leases": entry.leases,
            }
            if isinstance(pool, QueuePool):
                pools[name].update(
                    size=pool.size(),
                    checked_in=pool.checkedin(),
                    checked_out=pool.checkedout(),
                    overflow=pool.overflow(),
                )
        return {
            "revision": self.revision,
            "pools": pools,
            "retiring": len(self._retired),
            "retirement_errors": [type(error).__name__ for error in self._retirement_errors],
            "query_observation": {
                "count": self._observation_count,
                "failures": self._observation_failures,
                "last_error_type": self._observation_error_type,
            },
        }

    def _retirement_done(self, task: asyncio.Task) -> None:
        self._retirement_tasks.discard(task)
        try:
            task.result()
        except BaseException as error:
            self._retirement_errors.append(error)

    async def _dispose_entries(self, entries) -> None:
        errors = []
        for entry in entries:
            entry.retired = True
            self._retired.add(entry)
            try:
                await entry.drained.wait()
                await entry.engine.dispose()
                listener = self._listeners.get(entry)
                if listener is not None:
                    listener.close()
                    del self._listeners[entry]
                self._retired.discard(entry)
                self._connectivity.pop(entry, None)
                self._replication_health.pop(entry, None)
            except BaseException as error:
                errors.append(error)
        CleanupUtils.raise_collected_cleanup_errors("数据源释放失败", errors)

    async def _cleanup_entries(self, entries, *, primary=None) -> None:
        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            lambda: self._dispose_entries(entries), "数据库引擎清理"
        )
        CleanupUtils.raise_collected_cleanup_errors(
            "数据库引擎清理失败",
            [] if error is None else [error],
            primary_error=primary,
            caller_cancellation=cancellation,
        )

    async def close(self) -> None:
        async with self._lock:
            self._accepting = False
            if self._retirement_tasks:
                await asyncio.gather(*tuple(self._retirement_tasks), return_exceptions=True)
            entries = set(self.entries.values()) | self._retired
            self.entries = {}
            errors = self._retirement_errors
            self._retirement_errors = []
            try:
                await self._cleanup_entries(entries)
            except BaseException as error:
                errors.append(error)
            CleanupUtils.raise_collected_cleanup_errors("数据库关闭失败", errors)
