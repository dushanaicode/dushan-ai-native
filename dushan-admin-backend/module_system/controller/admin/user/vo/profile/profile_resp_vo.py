from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from module_system.controller.admin.dept.vo.dept.dept_simple_resp_vo import DeptSimpleRespVO
from module_system.controller.admin.dept.vo.post.post_simple_resp_vo import PostSimpleRespVO
from module_system.controller.admin.permission.vo.role.role_simple_resp_vo import RoleSimpleRespVO


class UserProfileRespVO(BaseVO):
    """管理后台 - 用户个人中心信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    username: Annotated[str, Field(..., description="用户账号")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    email: Annotated[str | None, Field(None, description="用户邮箱")]
    mobile: Annotated[str | None, Field(None, description="手机号码")]
    sex: Annotated[int | None, Field(None, description="用户性别，参见 CommonSexEnum 枚举类")]
    avatar: Annotated[str | None, Field(None, description="用户头像")]
    login_ip: Annotated[str, Field(..., description="最后登录 IP")]
    login_date: Annotated[datetime, Field(..., description="最后登录时间")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    roles: Annotated[list[RoleSimpleRespVO] | None, Field(None, description="所属角色")]
    dept: Annotated[DeptSimpleRespVO | None, Field(None, description="所在部门")]
    posts: Annotated[list[PostSimpleRespVO] | None, Field(None, description="所属岗位数组")]
    bio: Annotated[str | None, Field(None, description="个人简介")]
    tags: Annotated[list[str] | None, Field(None, description="用户标签")]
    address: Annotated[str | None, Field(None, description="地址")]
    skills: Annotated[list[str] | None, Field(None, description="技能标签")]
    work_scope: Annotated[str | None, Field(None, description="工作职责描述")]
    expertise: Annotated[str | None, Field(None, description="专业领域")]
    communication_style: Annotated[str | None, Field(None, description="沟通风格")]
    ai_preference: Annotated[dict | None, Field(None, description="AI 交互偏好")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "dushan",
                    "nickname": "渡山",
                    "email": "docker@dushan.cn",
                    "mobile": "18888888888",
                    "sex": 1,
                    "avatar": "https://www.dushan.cn/xxx.png",
                    "loginIp": "192.168.1.1",
                    "loginDate": "2020-05-20 05:20:00",
                    "createTime": "2020-05-20 05:20:00",
                    "roles": [],
                    "dept": {},
                    "posts": [],
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
