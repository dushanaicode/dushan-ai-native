from http import HTTPStatus

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class ConflictException(BaseBusinessException):
    """冲突异常：用于唯一键冲突、并发更新冲突、状态机不允许等场景。"""

    default_error_code = GlobalErrorCodeConstants.CONFLICT
    http_status = HTTPStatus.CONFLICT
