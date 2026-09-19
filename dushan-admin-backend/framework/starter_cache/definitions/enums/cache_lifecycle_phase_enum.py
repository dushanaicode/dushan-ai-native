from framework.common.enums.base_enum import BaseEnum


class CacheLifecyclePhaseEnum(BaseEnum):
    """缓存连接管理器的生命周期阶段；只有 READY 允许取用客户端。"""

    STOPPED = ("stopped", "已停止")
    INITIALIZING = ("initializing", "初始化中")
    READY = ("ready", "可用")
    CLOSING = ("closing", "关闭中")
    CLOSE_FAILED = ("close_failed", "关闭失败")
