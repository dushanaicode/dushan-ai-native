from typing import Literal

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException

type DataPermissionFailure = Literal[
    "missing", "denied", "stale", "configuration", "provider", "unregistered", "write", "closed"
]


class DataPermissionException(BaseBusinessException):
    """错误响应不包含身份、授权范围、SQL、凭据或 Provider 的消息。"""

    log_level = LogLevelEnum.INFO

    def __init__(self, reason: DataPermissionFailure, *, cause: Exception | None = None):
        unavailable = reason in {"configuration", "provider", "unregistered", "closed"}
        messages = {
            "missing": "数据权限主体不可用",
            "denied": "数据范围拒绝访问",
            "stale": "数据权限快照已失效",
            "configuration": "数据权限配置无效",
            "provider": "数据权限提供者不可用",
            "unregistered": "模型未声明数据访问策略",
            "write": "写入包含未授权记录或归属字段",
            "closed": "数据权限服务已关闭",
        }
        if unavailable:
            self.log_level = LogLevelEnum.ERROR
        super().__init__(
            GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
            if unavailable
            else GlobalErrorCodeConstants.FORBIDDEN,
            msg=messages[reason],
            cause=cause,
        )
        self.reason = reason

    def __safe_diagnostic__(self):
        return DataPermissionException(self.reason)
