from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.exception import ModelValidatorException
from framework.common.schemas import BaseRequestVO
from framework.common.validator import Email, Length, Mobile, NotEmpty, Pattern, Size
from framework.starter_security.public import (
    DiffField,
)


class UserSaveReqVO(BaseRequestVO):
    """管理后台 - 用户创建/修改 Request VO"""

    id: Annotated[
        SnowflakeIdInput | None,
        DiffField(name="", ignore=True),
        Field(default=None, description="用户编号"),
    ]
    username: Annotated[str, DiffField(name="用户账号"), Field(..., description="用户账号")]
    nickname: Annotated[str, DiffField(name="用户昵称"), Field(..., description="用户昵称")]
    remark: Annotated[str | None, DiffField(name="备注"), Field(default=None, description="备注")]
    dept_id: Annotated[
        SnowflakeIdInput | None,
        DiffField(name="部门", formatter="get_dept_by_id"),
        Field(default=None, description="部门编号"),
    ]
    post_ids: Annotated[
        list[SnowflakeIdInput] | None,
        DiffField(name="岗位", formatter="get_post_by_id"),
        Field(default=None, description="岗位编号数组"),
    ]
    email: Annotated[
        str | None, DiffField(name="用户邮箱"), Field(default=None, description="用户邮箱")
    ]
    mobile: Annotated[
        str | None, DiffField(name="手机号码"), Field(default=None, description="手机号码")
    ]
    sex: Annotated[
        int | None,
        DiffField(name="用户性别", formatter="get_sex"),
        Field(default=None, description="用户性别"),
    ]
    avatar: Annotated[
        str | None, DiffField(name="用户头像"), Field(default=None, description="用户头像")
    ]
    password: Annotated[
        str | None, DiffField(name="", ignore=True), Field(default=None, description="密码")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "username": "dushan",
                    "nickname": "渡山",
                    "remark": "我是一个用户",
                    "deptId": 1024,
                    "postIds": [1],
                    "email": "729227973@qq.com",
                    "mobile": "18888888888",
                    "sex": 1,
                    "avatar": "https://www.dushan.info/xxx.png",
                    "password": "123456",
                }
            ]
        }
    }

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username_not_empty_pattern_size(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="username", value=v, error_msg="用户账号不能为空")
        Pattern.require_pattern(
            field_name="username",
            value=v,
            pattern="^[a-zA-Z0-9]+$",
            error_msg="用户账号由 数字、字母 组成",
        )
        Size.require_size(
            field_name="username",
            value=v,
            min_length=4,
            max_length=30,
            error_msg="用户账号长度为 4-30 个字符",
        )
        return v

    @field_validator("nickname", mode="before")
    @classmethod
    def _validate_nickname_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="nickname",
                value=v,
                min_length=0,
                max_length=30,
                error_msg="用户昵称长度不能超过30个字符",
            )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email_format_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Email.require_email(field_name="email", value=v, error_msg="邮箱格式不正确")
            Size.require_size(
                field_name="email",
                value=v,
                min_length=0,
                max_length=50,
                error_msg="邮箱长度不能超过 50 个字符",
            )
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile_format(cls, v: str | None) -> str | None:
        if v is not None:
            Mobile.require_mobile(field_name="mobile", value=v, error_msg="手机号格式不正确")
        return v

    @model_validator(mode="before")
    @classmethod
    def check_password_logic(cls, values: Any) -> Any:
        """
        校验密码逻辑：
        1. 创建用户 (id is None): 密码不能为空，且长度必须为 4-16 位。
        2. 更新用户 (id is not None)
        """
        if isinstance(values, dict):
            id_val = values.get("id")
            password = values.get("password")
        elif hasattr(values, "id"):
            id_val = values.id
            password = getattr(values, "password", None)
        else:
            raise ModelValidatorException(
                msg=f"check_password_logic 无法处理类型为 {type(values)} 的输入"
            )
        is_create = id_val is None
        if is_create:
            NotEmpty.require_not_empty("password", password, "创建用户时密码不能为空")
            Length.require_length(
                field_name="password",
                value=password,
                min_length=4,
                max_length=16,
                error_msg="密码长度必须为 4-16 位",
            )
        return values
