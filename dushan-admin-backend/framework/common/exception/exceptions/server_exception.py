from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class ServerException(BaseBusinessException):
    """服务端异常：用于系统异常场景。"""

    default_error_code = GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
    log_level = "ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    retryable = True
