from typing import Literal

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException

type TenantFailure = Literal[
    "missing",
    "unknown",
    "disabled",
    "denied",
    "configuration",
    "mode",
    "model",
    "write",
    "expired",
    "closed",
]


class TenantException(BaseBusinessException):
    """租户失败只公开稳定原因，不暴露身份、SQL 和 Provider 返回内容。"""

    def __init__(self, reason: TenantFailure, *, cause: Exception | None = None):
        messages = {
            "missing": "缺少有效租户上下文",
            "unknown": "租户不存在",
            "disabled": "租户不可用",
            "denied": "租户访问未获授权",
            "configuration": "租户资源或提供者未就绪",
            "mode": "租户部署模式与封存记录不一致，请通过独立部署入口切换",
            "model": "模型租户归属、唯一键或关联约束无效",
            "write": "写入违反租户归属",
            "expired": "租户执行授权已失效",
            "closed": "租户运行时已关闭",
        }
        super().__init__(
            GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
            if reason in {"configuration", "mode", "model", "closed"}
            else GlobalErrorCodeConstants.FORBIDDEN,
            msg=messages[reason],
            cause=cause,
        )
        self.reason = reason

    def __safe_diagnostic__(self):
        return TenantException(self.reason)
