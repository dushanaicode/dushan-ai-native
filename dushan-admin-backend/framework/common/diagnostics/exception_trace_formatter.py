import traceback

from framework.common.security.sanitizer import Sanitizer


class ExceptionTraceFormatter:
    """格式化并脱敏异常链，供日志、调试响应和终端报告共用。

    使用 format(exc) 获取保留换行的文本列表；格式化失败时返回异常类型
    和失败类型，不把诊断故障替换为调用方正在处理的原始异常。
    """

    @staticmethod
    def format(exc: BaseException) -> list[str]:
        """保留异常链和堆栈并脱敏，格式化失败时仅返回异常类型。"""
        try:
            trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            return Sanitizer.sanitize_text(trace).splitlines(keepends=True)
        except Exception as formatting_error:
            return [f"{type(exc).__name__}: 堆栈格式化失败（{type(formatting_error).__name__}）\n"]
