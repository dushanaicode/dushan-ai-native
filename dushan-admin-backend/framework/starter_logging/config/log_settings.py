import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from framework.starter_logging.enums.log_file_type_enum import LogFileTypeEnum
from framework.starter_logging.enums.log_level_enum import LogLevelEnum

DEFAULT_LOG_ROTATION_SIZE = "20 MB"
DEFAULT_INFO_RETENTION = "7 days"
DEFAULT_WARNING_RETENTION = "15 days"
DEFAULT_ERROR_RETENTION = "30 days"


class LogSettings(BaseModel):
    """配置控制台、分级文件和结构化日志，交给 LoggingStarter 初始化。

    通过 application.yaml 的 log 分组及 LOG_* 环境变量覆盖。
    文件写入由 enable_file_overall 控制，压测模式下强制关闭文件输出。
    root_dir 是实际日志目录；测试必须关闭文件输出或显式使用 Temp 内的路径。
    """

    root_dir: str | None = Field(default=None, description="日志输出根目录。为空时使用 server/logs")
    enable_file_overall: bool = Field(
        default=True, description="是否启用文件日志总开关。如果为False，所有文件日志都不会写入。"
    )
    enable_json_format: bool = Field(default=False, description="是否启用 JSON 结构化日志")
    loadtest_mode: bool = Field(
        default=False,
        description="压力测试模式：关闭文件日志写入并提升控制台日志级别。",
    )
    console_level: LogLevelEnum = Field(
        default=LogLevelEnum.DEBUG, description="控制台输出的最低级别"
    )
    file_active_types: set[LogFileTypeEnum] = Field(
        default_factory=lambda: {LogFileTypeEnum.WARNING, LogFileTypeEnum.ERROR},
        description="激活的文件日志类型集合。",
    )
    rotation_size: str = Field(
        default=DEFAULT_LOG_ROTATION_SIZE, min_length=1, description="日志轮转大小"
    )
    enqueue: bool = Field(default=True, description="是否启用异步写入")
    compression: str | None = Field(default="zip", description="日志压缩格式，None 表示不压缩")
    file_level_info: LogLevelEnum = Field(
        default=LogLevelEnum.INFO, description="Info 日志文件的最低记录级别"
    )
    retention_info: str = Field(
        default=DEFAULT_INFO_RETENTION, min_length=1, description="Info 日志保留时间"
    )
    file_level_warning: LogLevelEnum = Field(
        default=LogLevelEnum.WARNING, description="Warning 日志文件的最低记录级别"
    )
    retention_warn: str = Field(
        default=DEFAULT_WARNING_RETENTION, min_length=1, description="Warning 日志保留时间"
    )
    file_level_error: LogLevelEnum = Field(
        default=LogLevelEnum.ERROR, description="Error 日志文件的最低记录级别"
    )
    retention_error: str = Field(
        default=DEFAULT_ERROR_RETENTION, min_length=1, description="Error 日志保留时间"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("file_active_types", mode="before")
    @classmethod
    def parse_file_active_types(cls, value):
        """支持 LOG_FILE_ACTIVE_TYPES 的 JSON 数组，例如 ["warning", "error"]。"""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("文件日志类型必须是 JSON 数组") from None
            if not isinstance(value, list):
                raise ValueError("文件日志类型必须是 JSON 数组")
        return value

    def get_effective_console_level(self) -> LogLevelEnum:
        """获取生效的控制台日志级别。"""
        if self.loadtest_mode:
            return LogLevelEnum.WARNING
        return self.console_level

    def get_effective_file_enabled(self) -> bool:
        """获取生效的文件日志开关。"""
        if self.loadtest_mode:
            return False
        return self.enable_file_overall
