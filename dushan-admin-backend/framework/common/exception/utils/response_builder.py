from typing import Any

from fastapi.encoders import jsonable_encoder

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.error_details import ErrorDetails
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)
from framework.common.security.sanitizer import Sanitizer


class ExceptionResponseBuilder:
    """构建code/message/data/error异常响应，公开详情与内部诊断分开处理。

    使用 build 生成可编码字典，HTTP 状态由上层异常处理器单独决定。
    仅当本次调用显式传入 debug=True 时包含脱敏上下文和堆栈。
    构建器无可变全局状态，不同应用分别传入自己的配置。
    """

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """将响应扩展数据转换为 JSON 可编码结构。"""
        try:
            return jsonable_encoder(value)
        except Exception:
            try:
                return str(value)
            except Exception:
                return f"<{type(value).__name__}>"

    @staticmethod
    def build(
        error_code: ErrorCode,
        message: str,
        data: Any = None,
        exc: Exception | None = None,
        *,
        error: ErrorDetails | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        """构建脱敏的错误响应，并按异常声明保留重试信息。"""
        # 先编码再脱敏，避免对象转换后的敏感文本绕过清理。
        safe_data = Sanitizer.sanitize_sensitive_data(ExceptionResponseBuilder._json_safe(data))
        details = (
            {}
            if error is None
            else error.model_dump(
                by_alias=True, exclude_none=True, exclude_defaults=True, exclude={"debug"}
            )
        )
        response: dict[str, Any] = {
            "code": error_code.code,
            "message": Sanitizer.sanitize_text(message),
            "data": safe_data,
            "error": None,
        }

        if isinstance(exc, BaseBusinessException) and exc.field_errors:
            details["fields"] = [item.model_dump() for item in exc.field_errors]

        # 业务异常可显式告诉调用方是否适合重试。
        if isinstance(exc, BaseBusinessException) and exc.retryable:
            details["retryable"] = True
            if exc.retry_after is not None:
                details["retryAfter"] = exc.retry_after

        # 仅调试模式包含上下文与堆栈，生产响应不暴露内部诊断信息。
        if debug and exc is not None:
            debug_info: dict[str, Any] = {
                "exception_type": type(exc).__name__,
            }
            if isinstance(exc, BaseBusinessException):
                if exc.context:
                    debug_info["context"] = exc.context
                if exc.__cause__:
                    cause_message = Sanitizer.sanitize_log_value(exc.__cause__)
                    debug_info["cause"] = f"{type(exc.__cause__).__name__}: {cause_message}"
            debug_info["stacktrace"] = ExceptionTraceFormatter.format(exc)
            details["debug"] = Sanitizer.sanitize_sensitive_data(
                ExceptionResponseBuilder._json_safe(debug_info)
            )

        if details:
            response["error"] = Sanitizer.sanitize_sensitive_data(
                ExceptionResponseBuilder._json_safe(details)
            )
        return response
