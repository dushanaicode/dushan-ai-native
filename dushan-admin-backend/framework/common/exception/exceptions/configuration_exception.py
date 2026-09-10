from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class ConfigurationException(BaseBusinessException):
    """配置异常：用于关键配置缺失/配置不合法等场景。"""

    default_error_code = GlobalErrorCodeConstants.ERROR_CONFIGURATION
    log_level = "ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
