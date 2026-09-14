from time import time_ns

from opentelemetry.trace import SpanKind, StatusCode

from framework.starter_database.connection.query_observation import QueryObservation
from framework.starter_database.spi.query_observer import QueryObserver
from framework.starter_monitor.core.monitor_service import MonitorService


class MonitorQueryObserver(QueryObserver):
    """只消费数据库已投影的事件，不访问Engine、原始SQL、参数或驱动异常。"""

    def __init__(self, monitor: MonitorService):
        self.monitor = monitor

    def observe(self, observation: QueryObservation) -> None:
        end = time_ns()
        attributes = {
            "db.operation.name": observation.operation,
            "db.namespace": observation.source,
            "db.query.summary": observation.template,
            "db.query.fingerprint": observation.fingerprint,
            "db.duration_ms": observation.elapsed_ms,
            "db.success": observation.success,
        }
        with self.monitor.span(
            f"db {observation.operation}",
            attributes,
            kind=SpanKind.CLIENT,
            start_time=end - int(observation.elapsed_ms * 1_000_000),
        ) as span:
            if not observation.success:
                span.set_status(StatusCode.ERROR)
            span.end(end)
