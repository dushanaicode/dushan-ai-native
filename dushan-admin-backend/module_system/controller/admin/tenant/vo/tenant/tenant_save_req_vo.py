from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
    SnowflakeReferenceInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.assert_true import AssertTrue
from framework.common.validator.length import Length
from framework.common.validator.not_null import NotNull
from framework.common.validator.pattern import Pattern
from framework.common.validator.size import Size


class TenantSaveReqVO(BaseRequestVO):
    """管理后台 - 租户创建 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="租户编号")]
    name: Annotated[str, Field(..., description="租户名")]
    contact_name: Annotated[str, Field(..., description="联系人")]
    contact_mobile: Annotated[str | None, Field(None, description="联系手机")]
    status: Annotated[int, Field(..., description="租户状态")]
    websites: Annotated[list[str] | None, Field(None, description="绑定域名列表")]
    package_id: Annotated[SnowflakeReferenceInput, Field(..., description="租户套餐编号")]
    expire_time: Annotated[datetime, Field(..., description="过期时间")]
    account_count: Annotated[int, Field(..., description="账号数量")]
    username: Annotated[str, Field(..., description="用户账号")]
    password: Annotated[str, Field(..., description="密码")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "contactName": "渡山",
                    "contactMobile": "18888888888",
                    "status": 1,
                    "websites": ["https://www.dushan.cn", "https://www.dushan2.cn"],
                    "packageId": 1024,
                    "expireTime": "2020-05-20T05:20:00Z",
                    "accountCount": 1024,
                    "username": "dushan",
                    "password": "123456",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="租户名不能为空")
        return v

    @field_validator("contact_name", mode="before")
    @classmethod
    def _validate_contact_name_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="contact_name", value=v, error_msg="联系人不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="租户状态不能为空")
        return v

    @field_validator("package_id", mode="before")
    @classmethod
    def _validate_package_id_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="package_id", value=v, error_msg="租户套餐编号不能为空")
        return v

    @field_validator("expire_time", mode="before")
    @classmethod
    def _validate_expire_time_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="expire_time", value=v, error_msg="过期时间不能为空")
        return v

    @field_validator("account_count", mode="before")
    @classmethod
    def _validate_account_count_not_null(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="account_count", value=v, error_msg="账号数量不能为空")
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username_pattern_size(cls, v: Any) -> Any:
        Pattern.require_pattern(
            field_name="username",
            value=v,
            pattern="^[a-zA-Z0-9]{4,30}$",
            error_msg="用户账号由数字、字母组成",
        )
        Size.require_size(
            field_name="username",
            value=v,
            min_length=4,
            max_length=30,
            error_msg="用户账号长度为 4-30 个字符",
        )
        return v

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password_length_not_empty(cls, v: Any) -> Any:
        Length.require_length(
            field_name="password",
            value=v,
            min_length=4,
            max_length=16,
            error_msg="密码长度为 4-16 位",
        )
        AssertTrue.require_true(field_name="password", value=bool(v), error_msg="密码不能为空")
        return v

    @model_validator(mode="before")
    def check_username_password(values):
        if values.get("id") is None and (not values.get("username") or not values.get("password")):
            raise ValueError("用户账号、密码不能为空")
        return values
