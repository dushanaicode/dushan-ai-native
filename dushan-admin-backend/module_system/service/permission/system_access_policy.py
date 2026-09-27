from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.starter_di.public import Inject, service
from framework.starter_security.public import SecurityContext, SecurityErrorCodes, SecurityException
from module_system.config.system_settings import SystemSettings
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.dal.mapper.permission.menu_mapper import MenuMapper
from module_system.dal.mapper.tenant.tenant_mapper import TenantMapper
from module_system.dal.mapper.tenant.tenant_package_mapper import TenantPackageMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants


@service()
class SystemAccessPolicy:
    OWNER_PAGES = frozenset(
        {
            "system/menu/index",
            "system/tenant/index",
            "system/tenantPackage/index",
            "infra/redis-cache/index",
        }
    )
    settings: SystemSettings = Inject()
    security: SecurityContext = Inject()
    tenants: TenantMapper = Inject()
    packages: TenantPackageMapper = Inject()
    menus: MenuMapper = Inject()

    def is_owner(self, user_id: int | str, tenant_id: str | None) -> bool:
        return (
            str(user_id) == self.settings.owner_user_id
            and tenant_id == self.settings.owner_tenant_id
        )

    def is_current_owner(self) -> bool:
        identity = self.security.require()
        return self.is_owner(identity.account_id, identity.tenant_id)

    def require_owner(self) -> None:
        if not self.is_current_owner():
            raise SecurityException(
                SecurityErrorCodes.DENIED, detail="仅作者超级管理员可执行此操作"
            )

    def protect_owner_account(self, user_id: int | str, tenant_id: str) -> None:
        if self.is_owner(user_id, tenant_id):
            self.require_owner()

    async def menu_ids(self, user_id: int | str, tenant_id: str) -> set[int]:
        """作者不受套餐限制，其余身份始终受当前套餐菜单上限约束。"""
        menus = await self.menus.select_list()
        if self.is_owner(user_id, tenant_id):
            return {menu.id for menu in menus}
        tenant = await self.tenants.select_by_id(int(tenant_id))
        if tenant is None:
            raise ServiceException(ErrorCodeConstants.TENANT_NOT_EXISTS)
        if tenant.package_id == TenantDO.PACKAGE_ID_SYSTEM:
            allowed = {menu.id for menu in menus}
        else:
            package = await self.packages.select_by_id(tenant.package_id)
            if package is None:
                raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_NOT_EXISTS)
            if package.status != StatusEnum.ENABLE.code:
                return set()
            allowed = set(package.menu_ids)
        return {
            menu.id
            for menu in menus
            if menu.id in allowed
            and not any(character in menu.permission for character in "*?[")
            and menu.component not in self.OWNER_PAGES
            and not menu.permission.startswith(("system:tenant:", "system:permission:menu:"))
            and not (
                menu.permission.startswith("infra:cache:")
                and menu.permission != "infra:cache:get-monitor-info"
            )
        }
