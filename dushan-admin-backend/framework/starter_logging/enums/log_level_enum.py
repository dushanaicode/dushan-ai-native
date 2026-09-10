from framework.common.enums.base_enum import BaseEnum


class LogLevelEnum(BaseEnum):
    """配置日志输出阈值，NONE 用于关闭对应输出。"""

    NONE = ("NONE", "关闭")
    TRACE = ("TRACE", "跟踪")
    DEBUG = ("DEBUG", "调试")
    INFO = ("INFO", "信息")
    SUCCESS = ("SUCCESS", "成功")
    WARNING = ("WARNING", "警告")
    ERROR = ("ERROR", "错误")
    CRITICAL = ("CRITICAL", "严重")
