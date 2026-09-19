from typing import Protocol

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.starter_logging.definitions.enums.log_file_type_enum import LogFileTypeEnum


class LoggerOptions(Protocol):
    """声明配置器实际读取的日志选项，配置模型实现这些字段和方法即可使用。"""

    root_dir: str
    enable_json_format: bool
    file_active_types: set[LogFileTypeEnum]
    rotation_size: str
    enqueue: bool
    compression: str | None
    file_level_info: LogLevelEnum
    retention_info: str
    file_level_warning: LogLevelEnum
    retention_warn: str
    file_level_error: LogLevelEnum
    retention_error: str
    loadtest_mode: bool

    def get_effective_console_level(self) -> LogLevelEnum:
        """返回最终生效的控制台日志级别。"""
        ...

    def get_effective_file_enabled(self) -> bool:
        """返回文件日志是否启用。"""
        ...
