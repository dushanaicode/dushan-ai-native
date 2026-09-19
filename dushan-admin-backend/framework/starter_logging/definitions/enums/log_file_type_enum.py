from framework.common.enums.base_enum import BaseEnum


class LogFileTypeEnum(BaseEnum):
    """区分普通、警告和错误日志文件。"""

    INFO = ("info", "Info 日志")
    WARNING = ("warning", "Warning 日志")
    ERROR = ("error", "Error 日志")
