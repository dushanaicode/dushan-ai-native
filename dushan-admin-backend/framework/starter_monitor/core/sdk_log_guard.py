import logging
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import ClassVar


class SdkLogGuard(logging.Filter):
    """仅屏蔽本组件调用中的SDK原始RPC诊断；安全摘要由应用诊断器输出。

    标准logging在此只作第三方适配，不安装handler或改变等级。过滤器按使用者计数，
    两个应用不会因其中一个关闭而失去保护，外部SDK调用的日志不受影响。
    """

    _quiet: ClassVar[ContextVar[bool]] = ContextVar("monitor_sdk_log_guard", default=False)
    _lock: ClassVar[Lock] = Lock()
    _users: ClassVar[int] = 0
    _filter: ClassVar["SdkLogGuard | None"] = None
    _names = (
        "opentelemetry.exporter.otlp.proto.grpc.exporter",
        "opentelemetry.baggage.propagation",
        "opentelemetry.trace.propagation.tracecontext",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        return not self._quiet.get()

    @classmethod
    def suppressed(cls) -> bool:
        return cls._quiet.get()

    @classmethod
    def acquire(cls) -> None:
        with cls._lock:
            if cls._users == 0:
                cls._filter = cls()
                for name in cls._names:
                    logging.getLogger(name).addFilter(cls._filter)
            cls._users += 1

    @classmethod
    def release(cls) -> None:
        with cls._lock:
            cls._users -= 1
            if cls._users == 0:
                for name in cls._names:
                    logging.getLogger(name).removeFilter(cls._filter)
                cls._filter = None

    @classmethod
    @contextmanager
    def quiet(cls):
        token = cls._quiet.set(True)
        try:
            yield
        finally:
            cls._quiet.reset(token)
