from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotNull


class FileCreateReqVO(BaseRequestVO):
    """管理后台 - 文件创建 Request VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="文件配置编号")]
    path: Annotated[str, Field(..., description="文件路径")]
    name: Annotated[str, Field(..., description="原文件名")]
    url: Annotated[str, Field(..., description="文件 URL")]
    type: Annotated[str | None, Field(default=None, description="文件 MIME 类型")]
    size: Annotated[int, Field(..., description="文件大小")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "configId": 11,
                    "path": "dushan.jpg",
                    "name": "dushan.jpg",
                    "url": "https://www.dushan.cn/dushan.jpg",
                    "type": "application/octet-stream",
                    "size": 2048,
                }
            ]
        }
    }

    @field_validator("config_id", mode="before")
    @classmethod
    def _validate_config_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="config_id", value=v, error_msg="文件配置编号不能为空")
        return v

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="path", value=v, error_msg="文件路径不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="原文件名不能为空")
        return v

    @field_validator("url", mode="before")
    @classmethod
    def _validate_url(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="url", value=v, error_msg="文件 URL不能为空")
        return v

    @field_validator("size", mode="before")
    @classmethod
    def _validate_size(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="size", value=v, error_msg="文件大小不能为空")
        return v
