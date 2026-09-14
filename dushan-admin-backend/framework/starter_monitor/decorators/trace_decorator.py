import inspect
from contextlib import contextmanager
from functools import wraps

from opentelemetry import trace

from framework.starter_monitor.core.monitor_service import MonitorService


class TraceDecorator:
    """共享同步/协程执行语义；生成器需专门的迭代生命周期，当前明确不接受。"""

    operation_name = ""

    def __call__(self, function):
        if inspect.isgeneratorfunction(function) or inspect.isasyncgenfunction(function):
            raise TypeError("追踪装饰器只支持同步函数和协程，不支持生成器")
        if getattr(function, "__monitor_traced__", False):
            raise ValueError("同一函数只能声明一个追踪装饰器")
        signature = inspect.signature(function)
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def asynchronous(*args, **kwargs):
                with self._scope(function, signature, args, kwargs):
                    return await function(*args, **kwargs)

            wrapped = asynchronous
        else:

            @wraps(function)
            def synchronous(*args, **kwargs):
                with self._scope(function, signature, args, kwargs):
                    return function(*args, **kwargs)

            wrapped = synchronous
        wrapped.__monitor_traced__ = True
        return wrapped

    @contextmanager
    def _scope(self, function, signature, args, kwargs):
        monitor = MonitorService.current()
        if monitor is None:
            yield trace.INVALID_SPAN
            return
        name = self.operation_name or f"{function.__module__}.{function.__qualname__}"
        with monitor.span(name, {"code.function.name": function.__qualname__}) as span:
            state = None
            if span.is_recording():
                state = monitor._observe(self.prepare, monitor, span, signature, args, kwargs)
            try:
                yield span
            finally:
                if span.is_recording():
                    monitor._observe(self.finish, monitor, span, state)

    def prepare(self, monitor, span, signature, args, kwargs):
        return None

    def finish(self, monitor, span, state):
        pass
