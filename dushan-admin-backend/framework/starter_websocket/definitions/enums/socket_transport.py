from framework.common.enums.base_enum import BaseEnum


class SocketTransport(BaseEnum):
    """跨连接分发消息使用的传输方式。"""

    LOCAL = ("local", "本地进程")
    REDIS = ("redis", "Redis 跨进程")
