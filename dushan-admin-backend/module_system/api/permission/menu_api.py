from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.permission.dto.menu_resp_dto import MenuRespDTO


@runtime_checkable
class MenuApi(Protocol):
    """菜单 API 接口"""

    async def get_menu(self, id: int) -> MenuRespDTO | None:
        """获得菜单信息"""
        ...

    async def get_menu_list(self, ids: Collection[int]) -> list[MenuRespDTO]:
        """获得菜单信息数组"""
        ...

    async def get_menu_map(self, ids: Collection[int]) -> dict[int, MenuRespDTO]:
        """获得指定编号的菜单 Map"""
        ...

    async def get_menu_ids_by_permissions(self, permissions: set[str]) -> dict[str, list[int]]:
        """根据权限码集合反查 menu_ids，返回 {permission: [menu_id, ...]} 映射"""
        ...
