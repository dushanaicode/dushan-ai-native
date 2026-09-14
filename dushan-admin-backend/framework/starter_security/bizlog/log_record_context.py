from contextlib import contextmanager
from contextvars import ContextVar

from framework.common.security.sanitizer import Sanitizer
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.bizlog.log_record_frame import LogRecordFrame


@framework(scope=ComponentScopeEnum.SINGLETON)
class LogRecordContext:
    """嵌套调用各自持有变量；只有当前 DI 执行和日志作用域可以读写。"""

    def __init__(self, application: ApplicationContext):
        self.application = application
        self._frame: ContextVar[LogRecordFrame | None] = ContextVar(
            f"bizlog_{id(self)}", default=None
        )
        self._values: ContextVar[dict] = ContextVar(f"bizlog_values_{id(self)}")

    @contextmanager
    def scope(self):
        binding = ApplicationContext.current_execution()
        if binding.application is not self.application:
            raise RuntimeError("业务日志的应用归属不一致")
        frame = LogRecordFrame(binding)
        token = self._frame.set(frame)
        values_token = self._values.set({})
        try:
            yield
        finally:
            frame.active = False
            self._frame.reset(token)
            self._values.reset(values_token)

    def _current(self):
        frame = self._frame.get()
        if (
            frame is None
            or not frame.active
            or frame.binding is not ApplicationContext.current_execution()
        ):
            raise RuntimeError("没有当前执行的业务日志作用域")
        return frame

    def put(self, name: str, value: object):
        self._current()
        # 只保存安全普通值；未知业务对象收敛为类型名，不调用其 repr。
        self._values.set({**self._values.get(), **Sanitizer.sanitize_log_value({name: value})})

    def values(self) -> dict:
        self._current()
        return dict(self._values.get())
