from typing import Protocol


class ExceptionTraceReporter(Protocol):
    """约定异常链路追踪的回调入口。

    实现 on_error 后注入 GlobalExceptionHandler。
    回调失败不会改变原异常响应；敏感异常只提供无原始引用的安全诊断投影。
    """

    def on_error(self, exc: Exception) -> None:
        """记录异常到外部链路追踪系统；敏感异常已由调用方生成安全投影。"""
        ...
