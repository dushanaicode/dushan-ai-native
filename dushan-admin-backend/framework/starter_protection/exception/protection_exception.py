from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes,
)


class ProtectionException(BaseBusinessException):
    """保留内部 cause；日志、追踪和 debug 输出只使用安全的错误码投影。"""

    _system_error_codes = frozenset(
        {
            ProtectionErrorCodes.UNAVAILABLE.code,
            ProtectionErrorCodes.CLOSED.code,
            ProtectionErrorCodes.CAPACITY.code,
        }
    )

    retryable = True

    def __safe_diagnostic__(self) -> "ProtectionException":
        return ProtectionException(self.error_code, retry_after=self.retry_after)
