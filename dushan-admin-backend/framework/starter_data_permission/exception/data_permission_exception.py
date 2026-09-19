from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)


class DataPermissionException(BaseBusinessException):
    """错误响应不包含身份、授权范围、SQL、凭据或 Provider 的消息。"""

    _system_error_codes = frozenset(
        {
            DataPermissionErrorCodes.CONFIGURATION.code,
            DataPermissionErrorCodes.PROVIDER.code,
            DataPermissionErrorCodes.UNREGISTERED.code,
            DataPermissionErrorCodes.CLOSED.code,
        }
    )

    log_level = LogLevelEnum.INFO

    def __init__(self, error_code: ErrorCode, *, cause: Exception | None = None):
        if error_code.code in self._system_error_codes:
            self.log_level = LogLevelEnum.ERROR
        super().__init__(error_code, msg=error_code.description, cause=cause)

    def __safe_diagnostic__(self):
        return DataPermissionException(self.error_code)
