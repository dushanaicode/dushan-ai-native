from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.service.user.admin_user_service import AdminUserService


@service
class AdminUserParseFunction:
    NAME = "get_admin_user_by_id"
    delegate: AdminUserService = Inject()

    async def apply(self, value):
        if value is None:
            return ""
        item = await self.delegate.get_user(int(value))
        return "" if item is None else item.nickname
