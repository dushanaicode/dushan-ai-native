from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator

from framework.common.schemas import BaseDTO


class AdminUserRespDTO(BaseDTO):
    """Admin 用户 Response DTO"""

    id: Annotated[int, Field(..., description="用户ID")]
    username: Annotated[str, Field(..., description="用户账号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    status: Annotated[int, Field(..., description="帐号状态")]
    dept_id: Annotated[int | None, Field(None, description="部门ID")]
    post_ids: Annotated[set[int], Field(default_factory=set, description="岗位编号数组")]
    mobile: Annotated[str | None, Field(None, description="手机号码")]
    avatar: Annotated[str | None, Field(None, description="用户头像")]

    @field_validator("post_ids", mode="before")
    @classmethod
    def normalize_posts(cls, value):
        return set() if value is None else value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "username": "admin",
                    "nickname": "管理员",
                    "status": 0,
                    "deptId": 100,
                    "postIds": [1, 2],
                    "mobile": "13800138000",
                    "avatar": "https://www.example.com/avatar.jpg",
                }
            ]
        }
    }
