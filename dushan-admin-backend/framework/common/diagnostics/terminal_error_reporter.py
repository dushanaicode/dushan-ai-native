import sys
import traceback

from framework.common.security.sanitizer import Sanitizer


class TerminalErrorReporter:
    """在日志不可用时将脱敏诊断同步写入 stderr。

    使用 report(operation, error, note_target) 保留原始失败信息；终端写入失败
    只向 note_target 添加附注，不覆盖主异常，也不依赖业务异常或日志系统。
    """

    @staticmethod
    def report(
        operation: str,
        error: BaseException,
        note_target: BaseException | None = None,
    ) -> None:
        """在日志基础设施不可用时，同步输出脱敏后的最终错误。"""
        try:
            error_trace = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            report = Sanitizer.sanitize_text(f"{operation}\n{error_trace}")
        except Exception as formatting_error:
            report = f"{operation}: {type(error).__name__}; traceback_format={type(formatting_error).__name__}"
        try:
            sys.stderr.write(f"{report.rstrip()}\n")
            sys.stderr.flush()
        except Exception as report_error:
            if note_target is not None:
                note_target.add_note(
                    f"Terminal stderr reporting failed: {type(report_error).__name__}"
                )
