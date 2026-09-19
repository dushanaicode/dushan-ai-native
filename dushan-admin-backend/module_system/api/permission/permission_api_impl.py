from __future__ import annotations

from typing import Collection, override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.permission.dto.dept_data_permission_resp_dto import DeptDataPermissionRespDTO
from module_system.api.permission.permission_api import PermissionApi
from module_system.service.permission.menu_service import MenuService
from module_system.service.permission.permission_service import PermissionService


@service(interface=PermissionApi)
class PermissionApiImpl(PermissionApi):
    """权限 API 实现类"""

    permission_service: PermissionService = Inject()
    menu_service: MenuService = Inject()

    @override
    async def get_user_menu_ids_from_cache(self, user_id: int) -> set[int]:
        return await self.permission_service.get_user_menu_list_by_user_id_from_cache(user_id)

    @override
    async def get_role_menu_ids(self, role_id: int) -> set[int]:
        return await self.permission_service.get_role_menu_list_by_role_id(role_id)

    @override
    async def get_role_menu_ids_by_role_ids(self, role_ids: Collection[int]) -> set[int]:
        return await self.permission_service.get_role_menu_list_by_role_ids(role_ids)

    @override
    async def get_user_permission_codes(self, user_id: int) -> set[str]:
        """获取用户权限码集合：菜单IDs(缓存) → 菜单列表 → permission 字段"""
        menu_ids = await self.permission_service.get_user_menu_list_by_user_id_from_cache(user_id)
        if not menu_ids:
            return set()
        menus = await self.menu_service.get_menu_list_by_ids(menu_ids)
        return {menu.permission for menu in menus if menu.permission}

    @override
    async def get_user_ids_by_role_ids(self, role_ids: Collection[int]) -> set[int]:
        return await self.permission_service.get_user_role_id_list_by_role_id(role_ids)

    @override
    async def has_any_permissions(self, user_id: int, *permissions: str) -> bool:
        return await self.permission_service.has_any_permissions(user_id, *permissions)

    @override
    async def has_any_roles(self, user_id: int, *roles: str) -> bool:
        return await self.permission_service.has_any_roles(user_id, *roles)

    @override
    async def get_dept_data_permission(self, user_id: int) -> DeptDataPermissionRespDTO:
        dept_perm = await self.permission_service.get_dept_data_permission(user_id)
        return DeptDataPermissionRespDTO.model_validate(dept_perm)
