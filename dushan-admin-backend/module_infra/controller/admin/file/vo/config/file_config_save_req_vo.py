from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotNull


class FileConfigSaveReqVO(BaseRequestVO):
    """管理后台 - 文件配置创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(default=None, description="编号")]
    name: Annotated[str, Field(..., description="配置名")]
    storage: Annotated[int, Field(..., description="存储器，参见 FileStorageEnum 枚举类")]
    config: Annotated[
        dict[str, Any], Field(..., description="存储配置,配置是动态参数，所以使用 Map 接收")
    ]
    remark: Annotated[str | None, Field(default=None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "S3 - 阿里云",
                    "storage": 1,
                    "config": {"key": "value"},
                    "remark": "备注",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="配置名不能为空")
        return v

    @field_validator("storage", mode="before")
    @classmethod
    def _validate_storage(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="storage", value=v, error_msg="存储器不能为空")
        return v

    @field_validator("config", mode="before")
    @classmethod
    def _validate_config(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="config", value=v, error_msg="存储配置不能为空")
        return v
