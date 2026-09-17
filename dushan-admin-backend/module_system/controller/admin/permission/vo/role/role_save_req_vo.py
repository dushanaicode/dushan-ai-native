from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size
from framework.starter_security.bizlog.diff_field import DiffField


class RoleSaveReqVO(BaseRequestVO):
    """管理后台 - 角色创建/更新 Request VO"""

    id: Annotated[
        SnowflakeIdInput | None,
        DiffField(name="", ignore=True),
        Field(default=None, description="角色编号"),
    ]
    name: Annotated[str, DiffField(name="角色名称"), Field(..., description="角色名称")]
    code: Annotated[str, DiffField(name="角色标志"), Field(..., description="角色标志")]
    sort: Annotated[int, DiffField(name="显示顺序"), Field(..., description="显示顺序")]
    remark: Annotated[str | None, DiffField(name="备注"), Field(default=None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"id": 1, "name": "管理员", "code": "ADMIN", "sort": 1024, "remark": "我是一个角色"}
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="角色名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=30,
            error_msg="角色名称长度不能超过 30 个字符",
        )
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="角色标志不能为空")
        Size.require_size(
            field_name="code",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="角色标志长度不能超过 100 个字符",
        )
        return v

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: int) -> int:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("remark", mode="before")
    @classmethod
    def _validate_remark(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="remark",
                value=v,
                min_length=0,
                max_length=500,
                error_msg="备注长度不能超过 500 个字符",
            )
        return v
