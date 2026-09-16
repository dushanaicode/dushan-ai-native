from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class MQException(BaseBusinessException):
    """诊断仅保留原因码，凭证和原始消息不会进入响应。"""

    def __init__(self, reason, *, cause=None):
        messages = {
            "configuration": "MQ 配置、声明或提供者未就绪",
            "declaration": "MQ 消费声明重复或不受后端支持",
            "closed": "MQ 运行时不可用",
            "capacity": "MQ 容量已满，发布被拒绝",
            "invalid": "MQ 消息格式或大小无效",
            "authentication": "MQ 消息认证失败",
            "expired": "MQ 消息已过期",
            "unknown": "MQ 发布或执行结果未知",
            "confirmation": "MQ 后端未确认消息",
            "lease": "MQ 消费租约已失效",
            "conflict": "MQ 消息标识与既有内容冲突",
        }
        super().__init__(
            GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
            if reason in {"configuration", "closed", "capacity", "unknown", "confirmation", "lease"}
            else GlobalErrorCodeConstants.BAD_REQUEST,
            msg=messages[reason],
            cause=cause,
        )
        self.reason = reason

    def __safe_diagnostic__(self):
        return MQException(self.reason)
