from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class RateLimitException(BaseBusinessException):
    """限流异常：用于触发限流/频控时抛出。"""

    default_error_code = GlobalErrorCodeConstants.TOO_MANY_REQUESTS
    http_status = HTTPStatus.TOO_MANY_REQUESTS
    retryable = True
    retry_after = 2
