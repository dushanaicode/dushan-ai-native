from __future__ import annotations

from module_system.service.tenant.handler.tenant_menu_handler import TenantMenuHandler


class RoleMenuIdFilterHandler(TenantMenuHandler):
    """根据租户允许的菜单ID过滤角色请求的菜单ID"""

    def __init__(self, requested_menu_ids: set[int]):
        self.requested_menu_ids = requested_menu_ids
        self.filtered_ids: set[int] = set()

    async def handle(self, allowed_menu_ids: set[int]) -> None:
        self.filtered_ids = self.requested_menu_ids.intersection(allowed_menu_ids)

    def get_filtered_ids(self) -> set[int]:
        return self.filtered_ids
