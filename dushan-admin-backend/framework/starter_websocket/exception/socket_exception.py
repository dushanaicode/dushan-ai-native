from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class SocketException(BaseBusinessException):
    """只发布安全原因，不携带原始帧、票据或完整主体。"""

    def __init__(self, reason, *, cause=None):
        messages = {
            "configuration": "WebSocket 声明、资源或认证提供者未就绪",
            "authentication": "WebSocket 会话认证失败",
            "policy": "WebSocket 访问未获授权",
            "protocol": "WebSocket 消息不符合协议",
            "unknown_type": "WebSocket 消息类型未登记",
            "too_large": "WebSocket 消息超过大小上限",
            "capacity": "WebSocket 连接或队列容量已满",
            "closed": "WebSocket 服务正在关闭",
            "transport": "WebSocket 传输不可用",
            "internal": "WebSocket 消息处理失败",
        }
        code = GlobalErrorCodeConstants.BAD_REQUEST
        if reason == "authentication":
            code = GlobalErrorCodeConstants.UNAUTHORIZED
        elif reason == "policy":
            code = GlobalErrorCodeConstants.FORBIDDEN
        elif reason in {"configuration", "closed", "capacity", "transport"}:
            code = GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
        super().__init__(code, msg=messages[reason], cause=cause)
        self.reason = reason

    def __safe_diagnostic__(self):
        return SocketException(self.reason)
