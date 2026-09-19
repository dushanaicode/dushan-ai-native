from collections.abc import Sequence
from typing import Any

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.field_error import FieldError
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.common.exception.exceptions.remote_error_detail import RemoteErrorDetail


class RemoteServiceException(BaseBusinessException):
    """表示远程服务调用失败，可通过 detail 保存仅供内部排错的上游详情。"""

    default_error_code = GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
    log_level = LogLevelEnum.ERROR
    is_system_error = True
    retryable = True

    def __init__(
        self,
        error_code: ErrorCode | None = None,
        msg: str | None = None,
        *,
        detail: RemoteErrorDetail | None = None,
        message_key: str | None = None,
        cause: Exception | None = None,
        context: dict[str, Any] | None = None,
        format_args: Sequence[Any] | None = None,
        retry_after: int | None = None,
        record_error: bool | None = None,
        field_errors: Sequence[FieldError] = (),
    ) -> None:
        """初始化远程服务异常并保存远程错误详情。"""
        super().__init__(
            error_code=error_code,
            msg=msg,
            message_key=message_key,
            cause=cause,
            context=context,
            format_args=format_args,
            retry_after=retry_after,
            record_error=record_error,
            field_errors=field_errors,
        )
        self.detail = detail
