from __future__ import annotations

from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.service.tenant.handler.tenant_menu_handler import TenantMenuHandler


class MenuListFilterHandler(TenantMenuHandler):
    """根据租户允许的菜单ID过滤原始菜单列表"""

    def __init__(self, original_menus: list[MenuDO]):
        self.original_menus: list[MenuDO] = original_menus
        self.filtered_result: list[MenuDO] = []

    async def handle(self, allowed_menu_ids: set[int]) -> None:
        self.filtered_result = [menu for menu in self.original_menus if menu.id in allowed_menu_ids]

    def get_filtered_menus(self) -> list[MenuDO]:
        return self.filtered_result
