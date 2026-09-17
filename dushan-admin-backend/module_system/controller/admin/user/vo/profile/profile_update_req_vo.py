from typing import Annotated

from pydantic import EmailStr, Field, HttpUrl, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.assert_true import AssertTrue
from framework.common.validator.size import Size


class UserProfileUpdateReqVO(BaseRequestVO):
    """管理后台 - 用户个人信息更新 Request VO"""

    nickname: Annotated[str | None, Field(None, description="用户昵称")]
    email: Annotated[EmailStr | None, Field(None, description="用户邮箱")]
    mobile: Annotated[str | None, Field(None, description="手机号码")]
    sex: Annotated[int | None, Field(None, description="用户性别，参见 CommonSexEnum 枚举类")]
    avatar: Annotated[HttpUrl | None, Field(None, description="角色头像")]
    bio: Annotated[str | None, Field(None, description="个人简介")]
    tags: Annotated[list[str] | None, Field(None, description="用户标签")]
    address: Annotated[str | None, Field(None, description="地址")]
    skills: Annotated[list[str] | None, Field(None, description="技能标签")]
    work_scope: Annotated[str | None, Field(None, description="工作职责描述")]
    expertise: Annotated[str | None, Field(None, description="专业领域")]
    communication_style: Annotated[
        str | None, Field(None, description="沟通风格（formal/casual/technical）")
    ]
    ai_preference: Annotated[dict | None, Field(None, description="AI 交互偏好")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nickname": "渡山",
                    "email": "729227973@qq.com",
                    "mobile": "18888888888",
                    "sex": 1,
                    "avatar": "https://www.dushan.info/xxx.png",
                    "bio": "富在术数，不在见识；利在势居，不在力耕。",
                    "tags": ["开发者", "设计师", "产品经理"],
                    "address": "中国・广东省・深圳市",
                    "skills": ["JavaScript", "HTML", "CSS", "Vue", "Node"],
                    "workScope": "前后端功能开发",
                    "expertise": "全栈开发",
                    "communicationStyle": "technical",
                    "aiPreference": {"responseStyle": "concise"},
                }
            ]
        }
    }

    @field_validator("nickname", mode="before")
    @classmethod
    def _validate_nickname_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="nickname",
                value=v,
                max_length=30,
                error_msg="用户昵称长度不能超过 30 个字符",
            )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="email", value=v, max_length=50, error_msg="邮箱长度不能超过 50 个字符"
            )
        return v

    @field_validator("mobile", mode="before")
    @classmethod
    def _validate_mobile_exact_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="mobile",
                value=v,
                min_length=11,
                max_length=11,
                error_msg="手机号长度必须 11 位",
            )
        return v

    @field_validator("bio", mode="before")
    @classmethod
    def _validate_bio_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="bio",
                value=v,
                max_length=500,
                error_msg="个人简介长度不能超过 500 个字符",
            )
        return v

    @field_validator("address", mode="before")
    @classmethod
    def _validate_address_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="address",
                value=v,
                max_length=255,
                error_msg="地址长度不能超过 255 个字符",
            )
        return v

    @field_validator("work_scope", mode="before")
    @classmethod
    def _validate_work_scope_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="work_scope",
                value=v,
                max_length=500,
                error_msg="工作职责描述长度不能超过 500 个字符",
            )
        return v

    @field_validator("expertise", mode="before")
    @classmethod
    def _validate_expertise_max_size(cls, v: str | None) -> str | None:
        if v is not None:
            Size.require_size(
                field_name="expertise",
                value=v,
                max_length=500,
                error_msg="专业领域长度不能超过 500 个字符",
            )
        return v

    @field_validator("communication_style", mode="before")
    @classmethod
    def _validate_communication_style(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = {"formal", "casual", "technical"}
            AssertTrue.require_true(
                field_name="communication_style",
                value=v in allowed,
                error_msg="沟通风格仅支持: formal, casual, technical",
            )
        return v
