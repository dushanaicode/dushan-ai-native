class WebSocketConstants:
    """消息声明、线协议与失效授权共用的固定取值。"""

    TYPE_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
    AUDIENCE_PATTERN = r"^[a-z][a-z0-9-]{0,63}$"
    BUILTIN_TYPES = frozenset({"ping", "pong", "error", "connect"})
    INVALIDATE_CAPABILITY = "websocket:invalidate"
