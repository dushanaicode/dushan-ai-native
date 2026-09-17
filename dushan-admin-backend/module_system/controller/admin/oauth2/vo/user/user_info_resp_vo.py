from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from module_system.controller.admin.oauth2.vo.user.dept import Dept
from module_system.controller.admin.oauth2.vo.user.post import Post


class OAuth2UserInfoRespVO(BaseVO):
    """管理后台 - OAuth2 用户基本信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    username: Annotated[str, Field(..., description="用户账号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    email: Annotated[str | None, Field(None, description="用户邮箱")]
    mobile: Annotated[str | None, Field(None, description="手机号码")]
    sex: Annotated[int | None, Field(None, description="用户性别，参见 CommonSexEnum 枚举类")]
    avatar: Annotated[str | None, Field(None, description="用户头像")]
    dept: Annotated[Dept | None, Field(None, description="所在部门")]
    posts: Annotated[list[Post] | None, Field(None, description="所属岗位数组")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "渡山",
                    "nickname": "渡山",
                    "email": "729227973@qq.com",
                    "mobile": "18888888888",
                    "sex": 1,
                    "avatar": "https://www.dushan.info/xxx.png",
                    "dept": {"id": 1, "name": "研发部"},
                    "posts": [{"id": 1, "name": "开发"}],
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="用户编号不能为空")
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="username", value=v, error_msg="用户账号不能为空")
        return v

    @field_validator("nickname", mode="before")
    @classmethod
    def _validate_nickname(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="nickname", value=v, error_msg="用户昵称不能为空")
        return v
