from http import HTTPStatus

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)


class PermissionException(BaseBusinessException):
    """权限异常：用于用户无权执行目标操作的场景。"""

    default_error_code = GlobalErrorCodeConstants.FORBIDDEN
    log_level = LogLevelEnum.INFO
    http_status = HTTPStatus.FORBIDDEN
