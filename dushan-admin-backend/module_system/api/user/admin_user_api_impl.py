from __future__ import annotations

from typing import Collection, override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.user.admin_user_api import AdminUserApi
from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO
from module_system.service.dept.dept_service import DeptService
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=AdminUserApi)
class AdminUserApiImpl(AdminUserApi):
    """Admin 用户 API 实现类"""

    user_service: AdminUserService = Inject()
    dept_service: DeptService = Inject()

    @override
    async def get_user(self, id: int) -> AdminUserRespDTO | None:
        user = await self.user_service.get_user(id)
        if user is None:
            return None
        return AdminUserRespDTO.model_validate(user)

    @override
    async def get_user_list_by_subordinate(self, id: int) -> list[AdminUserRespDTO]:
        depts = await self.dept_service.get_dept_list_by_leader_user_id(id)
        if not depts:
            return []
        dept_ids = {dept.id for dept in depts}
        child_dept_list = await self.dept_service.get_child_dept_list_by_ids(dept_ids)
        if child_dept_list:
            dept_ids.update({dept.id for dept in child_dept_list})
        users = await self.user_service.get_user_list_by_dept_ids(dept_ids)
        return [AdminUserRespDTO.model_validate(user) for user in users if user.id != id]

    @override
    async def get_user_list(self, ids: Collection[int]) -> list[AdminUserRespDTO]:
        users = await self.user_service.get_user_list(ids)
        return [AdminUserRespDTO.model_validate(user) for user in users]

    @override
    async def get_user_list_by_dept_ids(self, dept_ids: Collection[int]) -> list[AdminUserRespDTO]:
        users = await self.user_service.get_user_list_by_dept_ids(dept_ids)
        return [AdminUserRespDTO.model_validate(user) for user in users]

    @override
    async def get_user_list_by_post_ids(self, post_ids: Collection[int]) -> list[AdminUserRespDTO]:
        users = await self.user_service.get_user_list_by_post_ids(post_ids)
        return [AdminUserRespDTO.model_validate(user) for user in users]

    @override
    async def get_user_map(self, ids: Collection[int]) -> dict[int, AdminUserRespDTO]:
        if not ids:
            return {}
        users = await self.get_user_list(ids)
        return {user.id: user for user in users}

    @override
    async def validate_user(self, id: int) -> None:
        await self.validate_user_list([id])

    @override
    async def validate_user_list(self, ids: Collection[int]) -> None:
        await self.user_service.validate_user_list(ids)

    @override
    async def check_user_exists(self, user_id: int) -> bool:
        user = await self.user_service.get_user(user_id)
        return user is not None

    @override
    async def get_user_nickname(self, user_id: int) -> str | None:
        user = await self.user_service.get_user(user_id)
        return user.nickname if user else None

    @override
    async def search_users(self, keyword: str, limit: int = 20) -> list[AdminUserRespDTO]:
        if not keyword:
            return []
        users = await self.user_service.search_by_keyword(keyword, limit)
        return [AdminUserRespDTO.model_validate(user) for user in users]
