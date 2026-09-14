from loguru import logger

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)
from framework.common.security.sanitizer import Sanitizer


class ExceptionLogger:
    """异常日志记录器：根据异常类型和级别分级记录日志。"""

    @staticmethod
    def log(exc: Exception, error_code: ErrorCode, msg: str, path: str) -> None:
        """按业务级别记录异常，高级别日志保留脱敏后的原始异常链。"""
        safe_msg = Sanitizer.sanitize_text(msg)
        safe_path = Sanitizer.sanitize_text(path)
        if isinstance(exc, BaseBusinessException):
            level = logger.level(exc.log_level.value)
            category = "业务异常"
        else:
            level = logger.level(LogLevelEnum.ERROR.value)
            category = "系统异常"
        if level.no >= logger.level(LogLevelEnum.ERROR.value).no:
            trace = "".join(ExceptionTraceFormatter.format(exc))
            logger.log(
                level.name,
                "{}: {}，消息: {}，路径: {}\n{}",
                category,
                error_code.code,
                safe_msg,
                safe_path,
                trace,
            )
        else:
            logger.log(
                level.name,
                "{}: {}，消息: {}，路径: {}",
                category,
                error_code.code,
                safe_msg,
                safe_path,
            )
