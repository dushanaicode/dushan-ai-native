from typing import Annotated, Any

from pydantic import EmailStr, Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
    SnowflakeReferenceInput,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotEmpty, NotNull, Size


class DeptSaveReqVO(BaseRequestVO):
    """管理后台 - 部门创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="部门编号")]
    name: Annotated[str, Field(..., description="部门名称")]
    parent_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="父部门 ID")]
    sort: Annotated[int, Field(..., description="显示顺序")]
    leader_user_id: Annotated[SnowflakeIdInput | None, Field(None, description="负责人的用户编号")]
    phone: Annotated[str | None, Field(None, description="联系电话")]
    email: Annotated[EmailStr | None, Field(None, description="邮箱")]
    status: Annotated[int, Field(..., description="状态,见 StatusEnum 枚举")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "parentId": 1024,
                    "sort": 1024,
                    "leaderUserId": 2048,
                    "phone": "18888888888",
                    "email": "729227973@qq.com",
                    "status": 1,
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="部门名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=1,
            max_length=30,
            error_msg="部门名称长度不能超过 30 个字符",
        )
        return v

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def _validate_phone(cls, v: Any) -> Any:
        Size.require_size(
            field_name="phone", value=v, max_length=11, error_msg="联系电话长度不能超过11个字符"
        )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, v: Any) -> Any:
        Size.require_size(
            field_name="email", value=v, max_length=50, error_msg="邮箱长度不能超过 50 个字符"
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="修改状态必须是 {value}"
        )
        return v
