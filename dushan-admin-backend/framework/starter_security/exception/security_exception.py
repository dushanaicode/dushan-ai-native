from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes


class SecurityException(BaseBusinessException):
    """认证、授权与系统故障使用应用码区分；原始原因只供内部诊断。"""

    _system_error_codes = frozenset(
        {
            SecurityErrorCodes.UNAVAILABLE.code,
            SecurityErrorCodes.CONFIGURATION.code,
            SecurityErrorCodes.CLOSED.code,
        }
    )

    log_level = LogLevelEnum.INFO

    def __init__(
        self,
        error_code: ErrorCode,
        *,
        cause: Exception | None = None,
        detail: str | None = None,
    ):
        msg = error_code.description
        if detail:
            msg = f"{msg}：{detail}"
        if error_code.code in self._system_error_codes:
            self.log_level = LogLevelEnum.ERROR
        super().__init__(error_code, msg=msg, cause=cause)

    @property
    def is_authentication_error(self) -> bool:
        """缺失、无效或失效的登录凭据需要重新认证。"""
        return self.error_code.code in {
            SecurityErrorCodes.MISSING.code,
            SecurityErrorCodes.INVALID.code,
            SecurityErrorCodes.EXPIRED.code,
            SecurityErrorCodes.REVOKED.code,
            SecurityErrorCodes.DISABLED.code,
            SecurityErrorCodes.CREDENTIALS.code,
        }

    def __safe_diagnostic__(self):
        return SecurityException(self.error_code)
