from collections.abc import Awaitable, Callable

from fastapi import Request
from loguru import logger

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.exception.core.error_code import ErrorCode

type ErrorLogWriter = Callable[[Request, Exception, ErrorCode, str], Awaitable[None]]


class ErrorLogRecorder:
    """调用当前应用注入的异步错误记录方法，不持有全局服务或缓存。

    将实例方法作为 writer 传入，再把本记录器交给 GlobalExceptionHandler。
    writer 接收 request、安全异常诊断、ErrorCode 和脱敏提示四个位置参数。
    写入失败不会替换原异常响应；敏感异常不向第三方暴露原始对象。
    """

    def __init__(self, writer: ErrorLogWriter) -> None:
        """保存当前应用负责写入诊断记录的异步回调。"""
        self._writer = writer

    async def record(
        self, request: Request, exc: Exception, error_code: ErrorCode, msg: str
    ) -> None:
        """调用写入回调，失败时输出脱敏诊断，取消信号继续传播。"""
        try:
            await self._writer(request, SafeExceptionDiagnostics.snapshot(exc), error_code, msg)
        except Exception as e:
            logger.debug(
                "记录错误日志失败（不影响响应）\n{}",
                "".join(ExceptionTraceFormatter.format(e)),
            )
