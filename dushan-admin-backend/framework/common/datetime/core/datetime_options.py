import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DateTimeOptions(BaseModel):
    """声明日期工具的时区、显示格式及范围容量，默认值仅来自公共 YAML。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    timezone: str = Field(min_length=1)
    format: str = Field(min_length=1)
    date_format: str = Field(min_length=1)
    time_format: str = Field(min_length=1)
    month_format: str = Field(min_length=1)
    year_format: str = Field(min_length=1)
    max_range_segments: int = Field(gt=0)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """启动时验证 IANA 时区名称，避免首次使用才失败。"""
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("必须使用有效的 IANA 时区") from exc
        return value

    @field_validator("format", "date_format", "time_format", "month_format", "year_format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        """只接受跨平台的数字日期指令，拒绝拼错或依赖本机语言的格式指令。"""
        remainder = re.sub(r"%[%YymdHIMSfzjUWwGuV]", "", value)
        if "%" in remainder:
            raise ValueError("日期格式包含不支持的指令")
        return value

    @field_validator("max_range_segments", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        """范围段数不接受布尔值。"""
        if isinstance(value, bool):
            raise ValueError("范围段数必须是正整数")
        return value
