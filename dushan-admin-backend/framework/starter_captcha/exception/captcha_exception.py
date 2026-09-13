from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class CaptchaException(BaseBusinessException):
    """原始 cause 留在内部，Native 日志和 debug 响应只使用安全投影。"""

    def __safe_diagnostic__(self) -> "CaptchaException":
        return CaptchaException(self.error_code, http_status=self.http_status)
