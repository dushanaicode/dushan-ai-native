from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseSettings(BaseModel):
    """配置下载响应的缓存、内存上限和传输方式。

    默认禁止缓存并作为附件下载；inline/public 仅用于业务确认允许的内容。
    配置不代替文件访问授权、文件类型审查或流式内容的业务校验。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    download_cache: Literal["no-store", "private", "public"]
    download_max_age: int = Field(ge=0)
    max_memory_bytes: int = Field(ge=1)
    file_chunk_size: int = Field(ge=1)
    attachment: bool

    @field_validator("download_max_age", "max_memory_bytes", "file_chunk_size", mode="before")
    @classmethod
    def reject_boolean_limits(cls, value: Any) -> Any:
        """大小和缓存秒数不接受布尔值。"""
        if isinstance(value, bool):
            raise ValueError("响应数值配置不能是布尔值")
        return value
