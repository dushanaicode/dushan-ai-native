from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class UserVO(BaseVO):
    """管理后台 - 登录用户信息 VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    avatar: Annotated[str, Field(..., description="用户头像")]
    dept_id: Annotated[SnowflakeIdStr | None, Field(None, description="部门编号")]
    username: Annotated[str, Field(..., description="用户账号")]
    email: Annotated[str | None, Field(default=None, description="用户邮箱")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "nickname": "渡山源码",
                    "avatar": "https://www.dushan.info/xx.jpg",
                    "deptId": 2048,
                    "username": "dushan",
                    "email": "729227973@qq.com",
                }
            ]
        }
    }
