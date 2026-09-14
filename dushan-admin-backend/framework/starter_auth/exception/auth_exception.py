from typing import Literal

from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class AuthException(BaseBusinessException):
    """不回显上游文本；outcome 描述请求结果是否确定，所有操作均不隐式重试。"""

    def __init__(
        self,
        error_code,
        *,
        outcome: Literal["not_sent", "rejected", "unknown"] = "not_sent",
        cause: Exception | None = None,
    ):
        super().__init__(error_code=error_code, cause=cause)
        self.outcome = outcome
        self.retryable = False

    def __safe_diagnostic__(self) -> "AuthException":
        return AuthException(self.error_code, outcome=self.outcome)
