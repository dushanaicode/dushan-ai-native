from __future__ import annotations

from typing import override

from loguru import logger

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.dept.dept_api import DeptApi
from module_system.api.dept.post_api import PostApi
from module_system.api.user.dto.user_profile_resp_dto import UserProfileRespDTO
from module_system.api.user.user_profile_api import UserProfileApi
from module_system.service.user.admin_user_service import AdminUserService
from module_system.service.user.user_profile_service import UserProfileService


@service(interface=UserProfileApi)
class UserProfileApiImpl(UserProfileApi):
    """用户画像 API 实现"""

    user_profile_service: UserProfileService = Inject()
    admin_user_service: AdminUserService = Inject()
    dept_api: DeptApi = Inject()
    post_api: PostApi = Inject()

    @override
    async def get_user_profile_for_ai(self, user_id: int) -> UserProfileRespDTO | None:
        """聚合查询用户画像"""
        user = await self.admin_user_service.get_user(user_id)
        if not user:
            logger.debug(f"【UserProfileApi】用户不存在: user_id={user_id}")
            return None
        profile = await self.user_profile_service.get_user_profile(user_id)
        dept_name: str | None = None
        if user.dept_id:
            try:
                dept = await self.dept_api.get_dept(user.dept_id)
                dept_name = dept.name if dept else None
            except Exception as e:
                logger.warning(
                    f"【UserProfileApi】获取部门失败（降级跳过）: dept_id={user.dept_id}, error={e}"
                )
        post_names: list[str] = []
        if user.post_ids:
            try:
                posts = await self.post_api.get_post_list(user.post_ids)
                post_names = [p.name for p in posts]
            except Exception as e:
                logger.warning(
                    f"【UserProfileApi】获取岗位失败（降级跳过）: post_ids={user.post_ids}, error={e}"
                )
        return UserProfileRespDTO(
            user_id=user.id,
            nickname=user.nickname,
            dept_name=dept_name,
            post_names=post_names,
            work_scope=profile.work_scope if profile else None,
            expertise=profile.expertise if profile else None,
            communication_style=profile.communication_style if profile else None,
            ai_preference=profile.ai_preference if profile else None,
            skills=profile.skills if profile else None,
        )
