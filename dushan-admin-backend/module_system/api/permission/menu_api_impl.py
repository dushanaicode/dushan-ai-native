from __future__ import annotations

from typing import Collection, override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.permission.dto.menu_resp_dto import MenuRespDTO
from module_system.api.permission.menu_api import MenuApi
from module_system.service.permission.menu_service import MenuService


@service(interface=MenuApi)
class MenuApiImpl(MenuApi):
    """菜单 API 实现类"""

    menu_service: MenuService = Inject()

    @override
    async def get_menu(self, id: int) -> MenuRespDTO | None:
        menu = await self.menu_service.get_menu(id)
        if menu is None:
            return None
        return MenuRespDTO.model_validate(menu)

    @override
    async def get_menu_list(self, ids: Collection[int]) -> list[MenuRespDTO]:
        menus = await self.menu_service.get_menu_list_by_ids(set(ids))
        return [MenuRespDTO.model_validate(menu) for menu in menus]

    @override
    async def get_menu_map(self, ids: Collection[int]) -> dict[int, MenuRespDTO]:
        if not ids:
            return {}
        menu_list = await self.get_menu_list(ids)
        return {menu.id: menu for menu in menu_list}

    @override
    async def get_menu_ids_by_permissions(self, permissions: set[str]) -> dict[str, list[int]]:
        if not permissions:
            return {}
        return await self.menu_service.get_menu_ids_by_permissions(permissions)
