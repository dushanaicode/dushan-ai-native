from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size


class PostSaveReqVO(BaseRequestVO):
    """管理后台 - 岗位创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="岗位编号")]
    name: Annotated[str, Field(..., description="岗位名称")]
    code: Annotated[str, Field(..., description="岗位编码")]
    sort: Annotated[int, Field(..., description="显示顺序")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "code": "dushan",
                    "sort": 1024,
                    "status": 1,
                    "remark": "快乐的备注",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="岗位名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=50,
            error_msg="岗位名称长度不能超过 50 个字符",
        )
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="岗位编码不能为空")
        Size.require_size(
            field_name="code",
            value=v,
            min_length=0,
            max_length=64,
            error_msg="岗位编码长度不能超过64个字符",
        )
        return v

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status",
            value=v,
            enum_class=StatusEnum,
            error_msg="状态必须在指定范围 {value}",
        )
        return v

    @field_validator("remark", mode="before")
    @classmethod
    def _validate_remark(cls, v: Any) -> Any:
        Size.require_size(
            field_name="remark", value=v, max_length=255, error_msg="备注长度不能超过 255 个字符"
        )
        return v
