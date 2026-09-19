from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class UserProfileRespDTO(BaseDTO):
    """用户画像 Response DTO（聚合画像 + 用户基础 + 部门 + 岗位）"""

    user_id: Annotated[int, Field(..., description="用户 ID")]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    dept_name: Annotated[str | None, Field(None, description="部门名称（来自 dept 关联）")]
    post_names: Annotated[
        list[str], Field(default_factory=list, description="岗位名称列表（来自 post 关联）")
    ]
    work_scope: Annotated[str | None, Field(None, description="工作职责描述")]
    expertise: Annotated[str | None, Field(None, description="专业领域")]
    communication_style: Annotated[str | None, Field(None, description="沟通风格")]
    ai_preference: Annotated[
        dict | None, Field(None, description="AI 交互偏好（用户主动设置，优先级最高）")
    ]
    skills: Annotated[list[str] | None, Field(None, description="技能标签")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1,
                    "nickname": "渡山",
                    "deptName": "技术部",
                    "postNames": ["技术总监"],
                    "workScope": "技术架构设计与团队管理",
                    "expertise": "微服务架构、云原生",
                    "communicationStyle": "technical",
                    "aiPreference": {"responseStyle": "concise"},
                    "skills": ["Python", "Go"],
                }
            ]
        }
    }
