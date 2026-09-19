from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_captcha.definitions.constants.captcha_error_codes import CaptchaErrorCodes


class CaptchaException(BaseBusinessException):
    """原始 cause 留在内部，Native 日志和 debug 响应只使用安全投影。"""

    _system_error_codes = frozenset(
        {
            CaptchaErrorCodes.DISABLED.code,
            CaptchaErrorCodes.UNAVAILABLE.code,
            CaptchaErrorCodes.CACHE_UNAVAILABLE.code,
            CaptchaErrorCodes.CORRUPT.code,
            CaptchaErrorCodes.PROVIDER_TIMEOUT.code,
            CaptchaErrorCodes.PROVIDER_FAILURE.code,
            CaptchaErrorCodes.PROVIDER_RESPONSE.code,
            CaptchaErrorCodes.RESOURCE.code,
        }
    )

    def __safe_diagnostic__(self) -> "CaptchaException":
        return CaptchaException(self.error_code)
