import traceback
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import Request
from loguru import logger

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.exception.core.error_code import ErrorCode
from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.error_log_record import ErrorLogRecord
from framework.starter_web.context.http_observation import HttpObservation

type ErrorLogWriter = Callable[[ErrorLogRecord], Awaitable[None]]


class ErrorLogRecorder:
    """调用当前应用注入的异步错误记录方法，不持有全局服务或缓存。

    将实例方法作为 writer 传入，再把本记录器交给 GlobalExceptionHandler。
    writer 只接收已规范化的 ErrorLogRecord，不再提取请求或异常诊断。
    写入失败不会替换原异常响应；敏感异常不向第三方暴露原始对象。
    """

    def __init__(self, writer: ErrorLogWriter) -> None:
        """保存当前应用负责写入诊断记录的异步回调。"""
        self._writer = writer

    async def record(
        self, request: Request, exc: Exception, error_code: ErrorCode, msg: str
    ) -> None:
        """调用写入回调，失败时输出脱敏诊断，取消信号继续传播。"""
        observation = HttpObservation.find(request.scope)
        context = observation.log_context if observation is not None else None
        token = (
            LogContext.bind_principal(
                context.account_id, context.tenant_id, context.membership_id, context.realm
            )
            if context is not None
            else None
        )
        try:
            context = LogContext.current()
            error = SafeExceptionDiagnostics.snapshot(exc)
            frame = next(reversed(traceback.extract_tb(error.__traceback__)), None)
            record = ErrorLogRecord(
                trace_id=context.trace_id or context.request_id or "",
                account_id=context.account_id,
                tenant_id=context.tenant_id,
                method=request.method,
                route=request.scope.get("state", {}).get("web_route_template", request.url.path)[
                    :255
                ],
                client_ip="" if context.client_ip is None else context.client_ip,
                user_agent=Sanitizer.sanitize_text(request.headers.get("user-agent", ""))[:200],
                exception_time=datetime.now(timezone.utc).replace(tzinfo=None),
                exception_name=type(error).__name__,
                exception_message=Sanitizer.sanitize_text(msg)[:512],
                exception_stack_trace="".join(ExceptionTraceFormatter.format(error)),
                exception_class_name=type(error).__module__,
                exception_file_name=frame.filename[-255:] if frame is not None else "",
                exception_method_name=frame.name[:255] if frame is not None else "",
                exception_line_number=frame.lineno if frame is not None else 0,
                result_code=error_code.code,
            )
            await self._writer(record)
        except Exception as e:
            logger.warning(
                "记录错误日志失败（不影响响应）\n{}",
                "".join(ExceptionTraceFormatter.format(e)),
            )
        finally:
            if token is not None:
                LogContext.reset(token)
