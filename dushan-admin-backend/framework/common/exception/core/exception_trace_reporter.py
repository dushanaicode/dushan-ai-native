from typing import Protocol


class ExceptionTraceReporter(Protocol):
    """约定异常链路追踪的回调入口。

    实现 on_error 后注入 GlobalExceptionHandler。
    回调失败不会改变原异常响应；异常原文仅供内部追踪系统使用。
    """

    @staticmethod
    def on_error(exc: Exception) -> None:
        """记录异常到外部链路追踪系统。"""
        ...
