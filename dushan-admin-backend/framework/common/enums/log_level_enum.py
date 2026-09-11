from framework.common.enums.base_enum import BaseEnum


class LogLevelEnum(BaseEnum):
    """统一日志输出阈值与异常日志级别，例如 LogLevelEnum.WARNING。

    value/code 是传给 Loguru 的级别名；NONE 仅用于关闭对应输出，不作为业务异常级别。
    """

    NONE = ("NONE", "关闭")
    TRACE = ("TRACE", "跟踪")
    DEBUG = ("DEBUG", "调试")
    INFO = ("INFO", "信息")
    SUCCESS = ("SUCCESS", "成功")
    WARNING = ("WARNING", "警告")
    ERROR = ("ERROR", "错误")
    CRITICAL = ("CRITICAL", "严重")
