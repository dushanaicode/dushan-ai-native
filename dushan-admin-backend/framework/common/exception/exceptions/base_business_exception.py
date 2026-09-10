from collections.abc import Sequence
from http import HTTPStatus
from typing import Any, ClassVar

from framework.common.exception.core.error_code import ErrorCode


class BaseBusinessException(Exception):
    """携带错误定义、展示提示和原始原因，可直接抛出或供业务异常继承。

    例如 raise BaseBusinessException(error_code, msg="资源不可用", cause=original_error)。
    子类可声明 default_error_code 并直接调用；基类本身必须显式提供错误码。
    error_code 和 msg 可按位置传入，其余元数据只能使用关键字参数。
    未传 msg 时使用错误定义的中文 description；message_key 和 format_args 供翻译层使用。
    参数示例：BaseBusinessException(error_code, msg="资源 {} 不可用", format_args=(name,))。
    普通格式错误回退默认提示并清空翻译参数，不覆盖错误码或原始原因。
    msg 和格式参数应能安全展示；context、__cause__ 和 traceback 仅供内部诊断，
    对外响应须经过响应构建器，不能直接序列化整个异常。
    """

    default_error_code: ClassVar[ErrorCode | None] = None
    log_level: str = "WARNING"
    http_status: int = HTTPStatus.BAD_REQUEST
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
        http_status: int | None = None,
        retry_after: int | None = None,
        record_error: bool | None = None,
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
        # HTTP 状态依次采用显式参数、错误定义和子类默认值，不从业务编号推导。
        if http_status is not None:
            self.http_status = http_status
        elif error_code.http_status is not None:
            self.http_status = error_code.http_status
        else:
            self.http_status = type(self).http_status
        self.retry_after = type(self).retry_after if retry_after is None else retry_after
        if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
            raise TypeError("http_status 必须是整数 HTTP 状态")
        if not 400 <= self.http_status <= 599:
            raise ValueError("业务异常的 http_status 必须在 400～599 之间")
        if self.retry_after is not None:
            if type(self.retry_after) is not int:
                raise TypeError("retry_after 必须是整数秒数")
            if self.retry_after < 0:
                raise ValueError("retry_after 不能为负数")
        self.record_error = type(self).record_error if record_error is None else record_error
        if type(self.record_error) is not bool:
            raise TypeError("record_error 必须是布尔值")

        self.error_code = error_code
        self.message_key = message_key or error_code.message_key
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
