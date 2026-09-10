from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class AuthException(BaseBusinessException):
    """认证异常：用于 Token 无效/过期/未登录等场景。"""

    default_error_code = GlobalErrorCodeConstants.UNAUTHORIZED
    log_level = "INFO"
    http_status = HTTPStatus.UNAUTHORIZED
