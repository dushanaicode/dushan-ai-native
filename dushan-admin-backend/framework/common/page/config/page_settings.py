from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PageSettings(BaseModel):
    """配置分页和全量读取边界，每个应用显式传给 DataPaginator。

    默认只允许普通分页；全量读取还需服务端调用 PageQuery.enable_fetch_all。
    这些配置不代替用户权限校验，接口不能从请求参数覆盖平台上限。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    default_size: int = Field(ge=1)
    max_size: int = Field(ge=1)
    fetch_all_enabled: bool
    fetch_all_max_rows: int = Field(ge=1)
    max_sort_fields: int = Field(ge=0)

    @field_validator(
        "default_size", "max_size", "fetch_all_max_rows", "max_sort_fields", mode="before"
    )
    @classmethod
    def reject_boolean_limits(cls, value: Any) -> Any:
        """数值边界不接受布尔值，环境变量的数值字符串仍由 Pydantic 解析。"""
        if isinstance(value, bool):
            raise ValueError("分页数值配置不能是布尔值")
        return value

    @model_validator(mode="after")
    def validate_default_size(self) -> Self:
        """默认页大小不能超过当前配置的最大页大小。"""
        if self.default_size > self.max_size:
            raise ValueError("default_size 不能大于 max_size")
        return self
