from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class WebSocketErrorCodes:
    """WebSocket 错误段 1_021_000～1_021_999。"""

    ERROR = ErrorCode(code=1_021_000, description="WebSocket 异常", message_key="websocket.error")
    CONFIGURATION = ErrorCode(
        code=1_021_001,
        description="WebSocket 声明、资源或认证提供者未就绪",
        message_key="websocket.configuration",
    )
    CLOSED = ErrorCode(
        code=1_021_002,
        description="WebSocket 服务正在关闭",
        message_key="websocket.closed",
    )
    CAPACITY = ErrorCode(
        code=1_021_003,
        description="WebSocket 连接或队列容量已满",
        message_key="websocket.capacity",
    )
    TRANSPORT = ErrorCode(
        code=1_021_004,
        description="WebSocket 传输不可用",
        message_key="websocket.transport",
    )

    AUTHENTICATION = ErrorCode(
        code=1_021_011,
        description="WebSocket 会话认证失败",
        message_key="websocket.authentication",
    )
    POLICY = ErrorCode(
        code=1_021_012,
        description="WebSocket 访问未获授权",
        message_key="websocket.policy",
    )

    PROTOCOL = ErrorCode(
        code=1_021_021,
        description="WebSocket 消息不符合协议",
        message_key="websocket.protocol",
    )
    UNKNOWN_TYPE = ErrorCode(
        code=1_021_022,
        description="WebSocket 消息类型未登记",
        message_key="websocket.unknown_type",
    )
    TOO_LARGE = ErrorCode(
        code=1_021_023,
        description="WebSocket 消息超过大小上限",
        message_key="websocket.too_large",
    )
    INTERNAL = ErrorCode(
        code=1_021_024,
        description="WebSocket 消息处理失败",
        message_key="websocket.internal",
    )
