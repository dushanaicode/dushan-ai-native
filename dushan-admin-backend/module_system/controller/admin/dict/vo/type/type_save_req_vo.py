from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotEmpty, NotNull, Size


class DictTypeSaveReqVO(BaseRequestVO):
    """管理后台 - 字典类型创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="字典类型编号")]
    name: Annotated[str, Field(..., description="字典名称")]
    type: Annotated[str, Field(..., description="字典类型")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "性别",
                    "type": "sys_common_sex",
                    "status": 1,
                    "remark": "快乐的备注",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="字典名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="字典类型名称长度不能超过100个字符",
        )
        return v

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type", value=v, error_msg="字典类型不能为空")
        Size.require_size(
            field_name="type",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="字典类型类型长度不能超过 100 个字符",
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        return v
