from starlette.exceptions import HTTPException

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)
from framework.common.security.sanitizer import Sanitizer


class ExceptionUtil:
    """从异常提取错误定义、可展示的提示和翻译键。

    业务异常保留自身错误定义；HTTP 异常使用明确的通用分类映射。
    一个 HTTP 状态可以对应多个业务错误码，不能将全部定义自动反转成此映射。
    """

    _STATUS_CODE_TO_ERROR_CODE: dict[int, ErrorCode] = {
        400: GlobalErrorCodeConstants.BAD_REQUEST,
        401: GlobalErrorCodeConstants.UNAUTHORIZED,
        403: GlobalErrorCodeConstants.FORBIDDEN,
        404: GlobalErrorCodeConstants.NOT_FOUND,
        405: GlobalErrorCodeConstants.METHOD_NOT_ALLOWED,
        409: GlobalErrorCodeConstants.CONFLICT,
        413: GlobalErrorCodeConstants.PAYLOAD_TOO_LARGE,
        422: GlobalErrorCodeConstants.VALIDATION_ERROR,
        423: GlobalErrorCodeConstants.LOCKED,
        429: GlobalErrorCodeConstants.TOO_MANY_REQUESTS,
        500: GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR,
        501: GlobalErrorCodeConstants.NOT_IMPLEMENTED,
        502: GlobalErrorCodeConstants.BAD_GATEWAY,
        503: GlobalErrorCodeConstants.SERVICE_UNAVAILABLE,
    }

    @staticmethod
    def get_error_code(exc: Exception) -> ErrorCode:
        """根据异常类型提取对应的错误定义。"""
        if isinstance(exc, BaseBusinessException):
            return exc.error_code
        if isinstance(exc, HTTPException):
            return ExceptionUtil._STATUS_CODE_TO_ERROR_CODE.get(
                exc.status_code, GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
            )
        return GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR

    @staticmethod
    def get_error_msg(exc: Exception) -> str:
        """提取异常消息并移除敏感内容。"""
        if isinstance(exc, BaseBusinessException):
            return Sanitizer.sanitize_text(exc.msg)
        if isinstance(exc, HTTPException) and isinstance(exc.detail, str) and exc.detail:
            return Sanitizer.sanitize_text(exc.detail)
        return Sanitizer.sanitize_text(str(exc))

    @staticmethod
    def get_message_key(exc: Exception) -> str | None:
        """提取异常对应的国际化消息 key。"""
        if isinstance(exc, BaseBusinessException):
            return exc.message_key

        error_code = ExceptionUtil.get_error_code(exc)
        return error_code.message_key
