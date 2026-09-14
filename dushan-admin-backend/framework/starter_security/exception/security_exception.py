from typing import Literal

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException

type SecurityFailure = Literal[
    "missing",
    "invalid",
    "expired",
    "revoked",
    "disabled",
    "credentials",
    "denied",
    "unavailable",
    "configuration",
    "closed",
]


class SecurityException(BaseBusinessException):
    """保留 Native 的 401/403/503 分类，内部原因独立于业务响应字段。"""

    log_level = LogLevelEnum.INFO

    def __init__(self, reason: SecurityFailure, *, cause: Exception | None = None):
        if reason == "denied":
            code = GlobalErrorCodeConstants.FORBIDDEN
        elif reason in {"unavailable", "configuration", "closed"}:
            code = GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
            self.log_level = LogLevelEnum.ERROR
        else:
            code = GlobalErrorCodeConstants.UNAUTHORIZED
        messages = {
            "missing": "用户未登录",
            "invalid": "无效的访问凭据",
            "expired": "访问凭据已过期",
            "revoked": "登录态已撤销",
            "disabled": "账号已禁用",
            "credentials": "凭据已失效",
            "denied": "权限不足",
            "unavailable": "安全依赖暂不可用",
            "configuration": "安全适配未配置",
            "closed": "安全服务不可用",
        }
        super().__init__(code, msg=messages[reason], cause=cause)
        self.reason = reason

    def __safe_diagnostic__(self):
        return SecurityException(self.reason)
