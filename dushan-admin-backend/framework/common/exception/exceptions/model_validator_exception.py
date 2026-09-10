from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class ModelValidatorException(BaseBusinessException, ValueError):
    """模型验证异常：用于 Pydantic 模型验证失败场景。"""

    default_error_code = GlobalErrorCodeConstants.VALIDATION_ERROR
    log_level = "INFO"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY
