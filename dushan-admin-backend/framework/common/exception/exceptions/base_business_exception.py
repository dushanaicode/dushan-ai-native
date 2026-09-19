from collections.abc import Sequence
from typing import Any, ClassVar

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.field_error import FieldError


class BaseBusinessException(Exception):
    """携带错误定义、展示提示和原始原因，可直接抛出或供业务异常继承。

    例如 raise BaseBusinessException(error_code, msg="资源不可用", cause=original_error)。
    子类可声明 default_error_code 并直接调用；基类本身必须显式提供错误码。
    error_code 和 msg 可按位置传入，其余元数据只能使用关键字参数。
    显式 message_key 优先用于翻译；仅传非空 msg 时保留最终提示，不再用默认翻译覆盖。
    未传有效 msg 时使用错误定义的中文 description，并允许翻译默认键。
    参数示例：BaseBusinessException(error_code, msg="资源 {} 不可用", format_args=(name,))。
    普通格式错误回退默认提示并清空翻译参数，不覆盖错误码或原始原因。
    msg 和格式参数应能安全展示；context、__cause__ 和 traceback 仅供内部诊断，
    对外响应须经过响应构建器，不能直接序列化整个异常。
    field_errors可显式提供公开字段错误，不从context或cause猜测表单字段。
    子类 log_level 使用 LogLevelEnum；不接受字符串或用于关闭输出的 NONE。
    故障分类、日志和重试策略由异常类声明，不依赖 HTTP 状态或编号大小。
    系统故障默认记录错误表，record_error 可独立覆盖；该标记不改变故障语义。
    """

    default_error_code: ClassVar[ErrorCode | None] = None
    log_level: LogLevelEnum = LogLevelEnum.WARNING
    is_system_error: bool = False
    _system_error_codes: ClassVar[frozenset[int]] = frozenset(
        {
            GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR.code,
            GlobalErrorCodeConstants.NOT_IMPLEMENTED.code,
            GlobalErrorCodeConstants.ERROR_CONFIGURATION.code,
            GlobalErrorCodeConstants.BAD_GATEWAY.code,
            GlobalErrorCodeConstants.SERVICE_UNAVAILABLE.code,
        }
    )
    retryable: bool = False
    retry_after: int | None = None
    record_error: bool = False

    def __init__(
        self,
        error_code: ErrorCode | None = None,
        msg: str | None = None,
        *,
        message_key: str | None = None,
        cause: Exception | None = None,
        context: dict[str, Any] | None = None,
        format_args: Sequence[Any] | None = None,
        retry_after: int | None = None,
        record_error: bool | None = None,
        field_errors: Sequence[FieldError] = (),
    ) -> None:
        """保存业务失败信息；畸形模板回退中文默认提示，取消和退出信号继续传播。"""
        if error_code is None:
            error_code = type(self).default_error_code
            if error_code is None:
                raise TypeError("必须传入 error_code，或在子类声明 default_error_code")
        if not isinstance(error_code, ErrorCode):
            raise TypeError("error_code 必须是 ErrorCode")
        if error_code.code == 0:
            raise ValueError("业务异常不能使用成功码 0")
        if msg is not None and not isinstance(msg, str):
            raise TypeError("msg 必须是字符串或 None")
        if message_key is not None and not isinstance(message_key, str):
            raise TypeError("message_key 必须是字符串或 None")
        if cause is not None and not isinstance(cause, Exception):
            raise TypeError("cause 必须是 Exception 或 None")
        if context is not None and not isinstance(context, dict):
            raise TypeError("context 必须是字典或 None")
        if format_args is not None and (
            not isinstance(format_args, Sequence)
            or isinstance(format_args, (str, bytes, bytearray))
        ):
            raise TypeError("format_args 必须是参数序列，不能是字符串")
        self.error_code = error_code
        self.is_system_error = (
            type(self).is_system_error or error_code.code in self._system_error_codes
        )
        self.retry_after = type(self).retry_after if retry_after is None else retry_after
        self.field_errors = tuple(field_errors)
        if any(not isinstance(item, FieldError) for item in self.field_errors):
            raise TypeError("field_errors只能包含FieldError")
        if self.retry_after is not None:
            if type(self.retry_after) is not int:
                raise TypeError("retry_after 必须是整数秒数")
            if self.retry_after < 0:
                raise ValueError("retry_after 不能为负数")
        self.record_error = type(self).record_error if record_error is None else record_error
        if type(self.record_error) is not bool:
            raise TypeError("record_error 必须是布尔值")
        if record_error is None and self.is_system_error:
            self.record_error = True
        if not isinstance(self.log_level, LogLevelEnum):
            raise TypeError("log_level 必须是 LogLevelEnum")
        if self.log_level is LogLevelEnum.NONE:
            raise ValueError("业务异常日志级别不能使用 NONE")

        self.message_key = message_key or error_code.message_key
        self._message_translation_enabled = bool(message_key) or not (msg and msg.strip())
        self.context = context or {}
        self.format_args: list[Any] = []
        self._message_format_failed = False

        # 格式参数的转换也可能失败，整个转换过程都不能覆盖业务异常。
        raw_msg = msg if msg and msg.strip() else error_code.description
        if format_args is not None:
            try:
                self.format_args = list(format_args)
                raw_msg = raw_msg.format(*self.format_args)
            except Exception:
                raw_msg = error_code.description
                self.format_args = []
                self._message_format_failed = True
            if not raw_msg.strip():
                raw_msg = error_code.description
                self.format_args = []
                self._message_format_failed = True

        self.msg = raw_msg
        super().__init__(self.msg)
        if cause is not None:
            self.__cause__ = cause
