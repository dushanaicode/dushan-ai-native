from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.user.dto.user_profile_resp_dto import UserProfileRespDTO


@runtime_checkable
class UserProfileApi(Protocol):
    """用户画像 API 接口（跨模块调用）"""

    async def get_user_profile_for_ai(self, user_id: int) -> UserProfileRespDTO | None:
        """获取用户聚合画像（含部门/岗位/AI 偏好）"""
        ...
