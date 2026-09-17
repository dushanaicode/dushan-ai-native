from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.permission.dto.dept_data_permission_resp_dto import DeptDataPermissionRespDTO


@runtime_checkable
class PermissionApi(Protocol):
    """权限 API 接口"""

    async def get_user_menu_ids_from_cache(self, user_id: int) -> set[int]:
        """从缓存中获取用户拥有的菜单 ID 集合"""
        ...

    async def get_role_menu_ids(self, role_id: int) -> set[int]:
        """获取角色拥有的菜单 ID 集合"""
        ...

    async def get_role_menu_ids_by_role_ids(self, role_ids: Collection[int]) -> set[int]:
        """批量获取多个角色拥有的菜单 ID 集合"""
        ...

    async def get_user_permission_codes(self, user_id: int) -> set[str]:
        """获取用户拥建立系统权限码集合（菜单 permission 字段）"""
        ...

    async def get_user_ids_by_role_ids(self, role_ids: Collection[int]) -> set[int]:
        """获取指定角色的用户 ID 集合"""
        ...

    async def has_any_permissions(self, user_id: int, *permissions: str) -> bool:
        """检查用户是否拥有指定的任一权限"""
        ...

    async def has_any_roles(self, user_id: int, *roles: str) -> bool:
        """检查用户是否拥有指定的任一角色"""
        ...

    async def get_dept_data_permission(self, user_id: int) -> DeptDataPermissionRespDTO:
        """获取用户的数据权限"""
        ...
