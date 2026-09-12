import random
from hashlib import sha256
from time import perf_counter
from typing import Callable

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.query_observation import QueryObservation
from framework.starter_database.connection.sql_template import SqlTemplate


class SlowQueryListener:
    """游标级有界观测；失败事件与错误翻译器共存，不返回或替换驱动异常。"""

    def __init__(
        self,
        engine: AsyncEngine,
        name: str,
        settings: DatabaseSettings,
        publish: Callable[[QueryObservation, bool], None],
        failed: Callable[[BaseException], None],
    ) -> None:
        self.engine, self.name, self.settings = engine, name, settings
        self._publish, self._failed = publish, failed
        event.listen(engine.sync_engine, "before_cursor_execute", self.before)
        event.listen(engine.sync_engine, "after_cursor_execute", self.after)
        event.listen(engine.sync_engine, "handle_error", self.error)

    def before(self, connection, cursor, statement, parameters, context, executemany):
        sampled = self.settings.query_observation_enabled and (
            self.settings.query_sample_rate == 1
            or (
                self.settings.query_sample_rate > 0
                and random.random() < self.settings.query_sample_rate
            )
        )
        context._dushan_query_observation = (
            (perf_counter(), sampled) if sampled or self.settings.slow_query_enabled else None
        )

    def after(self, connection, cursor, statement, parameters, context, executemany):
        self._finish(context, statement, success=True)

    def error(self, exception_context):
        context = exception_context.execution_context
        if context is not None:
            self._finish(context, exception_context.statement, success=False)

    def _finish(self, context, statement, *, success: bool) -> None:
        state = getattr(context, "_dushan_query_observation", None)
        if state is None:
            return
        context._dushan_query_observation = None
        started, sampled = state
        elapsed = (perf_counter() - started) * 1000
        if not sampled and elapsed < self.settings.slow_query_threshold_ms:
            return
        try:
            operation, template = SqlTemplate.render(
                statement or "", max_length=self.settings.query_max_statement_length
            )
            fingerprint = (
                sha256(template.encode("ascii")).hexdigest()
                if template is not None and self.settings.query_fingerprint_enabled
                else None
            )
            observation = QueryObservation(
                source=self.name,
                operation=operation,
                template=(
                    template[: self.settings.query_max_template_length]
                    if template is not None and self.settings.query_template_enabled
                    else None
                ),
                fingerprint=fingerprint,
                elapsed_ms=elapsed,
                success=success,
            )
            self._publish(observation, sampled)
        except BaseException as error:
            # 观测边界隔离所有消费者失败（包括同步消费者误抛取消），不改变写入结果。
            self._failed(error)

    def close(self) -> None:
        event.remove(self.engine.sync_engine, "before_cursor_execute", self.before)
        event.remove(self.engine.sync_engine, "after_cursor_execute", self.after)
        event.remove(self.engine.sync_engine, "handle_error", self.error)
