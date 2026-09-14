from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class ProtectionException(BaseBusinessException):
    """保留内部 cause；日志、追踪和 debug 输出只使用安全的错误码投影。"""

    retryable = True

    def __safe_diagnostic__(self) -> "ProtectionException":
        return ProtectionException(self.error_code, retry_after=self.retry_after)
