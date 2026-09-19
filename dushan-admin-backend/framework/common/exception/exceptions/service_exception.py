from collections.abc import Sequence
from typing import Any

from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.field_error import FieldError
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class ServiceException(BaseBusinessException):
    """表示业务逻辑失败，并为消息模板传入位置参数。

    例如 raise ServiceException(error_code, name)，用 name 替换消息中的 {}。
    错误码必须显式提供，其余位置参数只用于格式化，元数据使用关键字传入。
    显式提示和格式化参数都必须可对外展示，消息解析与回退由基类处理。
    """

    def __init__(
        self,
        error_code: ErrorCode,
        *args: Any,
        msg: str | None = None,
        message_key: str | None = None,
        cause: Exception | None = None,
        context: dict[str, Any] | None = None,
        retry_after: int | None = None,
        record_error: bool | None = None,
        field_errors: Sequence[FieldError] = (),
    ) -> None:
        """初始化业务服务异常并整理消息格式化参数。"""
        super().__init__(
            error_code=error_code,
            msg=msg,
            message_key=message_key,
            cause=cause,
            context=context,
            format_args=args if args else None,
            retry_after=retry_after,
            record_error=record_error,
            field_errors=field_errors,
        )
