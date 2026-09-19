from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes


class TenantException(BaseBusinessException):
    """租户失败只公开稳定原因，不暴露身份、SQL 和 Provider 返回内容。"""

    _system_error_codes = frozenset(
        {
            TenantErrorCodes.CONFIGURATION.code,
            TenantErrorCodes.MODE.code,
            TenantErrorCodes.MODEL.code,
            TenantErrorCodes.CLOSED.code,
        }
    )

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
        super().__init__(error_code, msg=msg, cause=cause)

    def __safe_diagnostic__(self):
        return TenantException(self.error_code)
