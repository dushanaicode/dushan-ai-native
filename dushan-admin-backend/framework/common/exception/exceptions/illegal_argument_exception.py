from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class IllegalArgumentException(BaseBusinessException):
    """参数异常：用于业务层主动校验请求参数不合法的场景。"""

    default_error_code = GlobalErrorCodeConstants.BAD_REQUEST
    log_level = "INFO"
