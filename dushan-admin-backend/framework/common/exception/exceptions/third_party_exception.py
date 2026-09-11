from http import HTTPStatus

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class ThirdPartyException(BaseBusinessException):
    """第三方异常：用于外部依赖（支付/短信/存储/地图等）调用失败"""

    default_error_code = GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
    log_level = LogLevelEnum.ERROR
    http_status = HTTPStatus.SERVICE_UNAVAILABLE
    retryable = True
