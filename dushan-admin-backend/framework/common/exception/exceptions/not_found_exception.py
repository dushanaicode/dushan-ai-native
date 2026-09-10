from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class NotFoundException(BaseBusinessException):
    """资源不存在异常：用于查询不到资源等场景。"""

    default_error_code = GlobalErrorCodeConstants.NOT_FOUND
    http_status = HTTPStatus.NOT_FOUND
