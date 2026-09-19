from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from sqlalchemy import select

from framework.common.dates import DateUtils
from framework.common.enums import BuiltinTypeEnum, StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    PasswordEncoder,
    SecurityErrorCodes,
    SecurityException,
    SecurityRealm,
    TenantAccessMode,
)
from framework.starter_tenant.public import (
    TenantAccessGrant,
    TenantContext,
    TenantInfo,
    TenantResourceGrant,
    TenantSettings,
)
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.dal.dataobject.permission.permission_user_role_do import UserRoleDO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.permission.role_menu_do import RoleMenuDO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.mapper.auth.system_authentication_mapper import SystemAuthenticationMapper
from module_system.dal.mapper.permission.menu_mapper import MenuMapper
from module_system.dal.mapper.permission.permission_user_role_mapper import PermissionUserRoleMapper
from module_system.dal.mapper.permission.role_mapper import RoleMapper
from module_system.dal.mapper.permission.role_menu_mapper import RoleMenuMapper
from module_system.dal.mapper.tenant.tenant_mapper import TenantMapper
from module_system.dal.mapper.tenant.tenant_package_mapper import TenantPackageMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.workload_constants import WorkloadConstants
from module_system.definitions.enums.permission.role_code_enum import (
    RoleCodeEnum,
)
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)
from module_system.service.tenant.tenant_service import TenantService


@service(interface=TenantService)
class TenantServiceImpl(TenantService):
    tenant_mapper: TenantMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def get_tenant_id_list(self, include_disabled: bool = False) -> list[int]:
        if include_disabled:
            tenants = await self.tenant_mapper.select_list()
        else:
            tenants = await self.get_tenant_list_by_status(StatusEnum.ENABLE.code)
        return [t.id for t in tenants]

    @override
    @transactional
    async def update_status(self, tenant_id: int, status: int) -> None:
        """更新租户状态"""
        await self._validate_update_tenant(tenant_id)
        update_obj = TenantDO(id=tenant_id, status=status)
        await self.tenant_mapper.update_by_id(update_obj)

    async def _valid_tenant_name_duplicate(self, name: str, id: int | None) -> None:
        tenant: TenantDO | None = await self.tenant_mapper.select_by_name(name)
        if tenant is None:
            return
        if id is None or tenant.id != id:
            raise ServiceException(ErrorCodeConstants.TENANT_NAME_DUPLICATE, name)

    async def _valid_tenant_website_duplicate(self, website: str | None, id: int | None) -> None:
        if not website or website.strip() == "":
            return
        tenant: TenantDO | None = await self.tenant_mapper.select_by_website(website)
        if tenant is None:
            return
        if id is None or tenant.id != id:
            raise ServiceException(ErrorCodeConstants.TENANT_WEBSITE_DUPLICATE, website)

    @override
    @transactional
    async def delete_tenant(self, id: int) -> None:
        await self._validate_update_tenant(id)
        await self.tenant_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_tenant_batch(self, ids: list[int]) -> int:
        for tenant_id in ids:
            await self._validate_update_tenant(tenant_id)
        return await self.tenant_mapper.delete_by_ids(ids)

    async def _validate_update_tenant(self, id: int) -> TenantDO:
        tenant: TenantDO | None = await self.tenant_mapper.select_by_id(id)
        if tenant is None:
            raise ServiceException(ErrorCodeConstants.TENANT_NOT_EXISTS)
        if tenant.package_id == TenantDO.PACKAGE_ID_SYSTEM:
            raise ServiceException(ErrorCodeConstants.TENANT_CAN_NOT_UPDATE_SYSTEM)
        return tenant

    @override
    async def get_tenant(self, id: int) -> TenantDO:
        return await self.tenant_mapper.select_by_id(id)

    @override
    async def get_tenant_page(self, page_req_vo: TenantPageReqVO) -> PageResult[TenantDO]:
        return await self.tenant_mapper.select_page(page_req_vo)

    @override
    async def get_tenant_list_by_status(self, status: int) -> list[TenantDO]:
        return await self.tenant_mapper.select_list_by_status(status)

    @override
    async def get_tenant_by_name(self, name: str) -> TenantDO:
        return await self.tenant_mapper.select_by_name(name)

    @override
    async def get_tenant_by_website(self, website: str) -> TenantDO:
        return await self.tenant_mapper.select_by_website(website)

    @override
    async def get_tenant_count_by_package_id(self, package_id: int) -> int:
        return await self.tenant_mapper.select_count_by_package_id(package_id)

    @override
    async def get_tenant_list_by_package_id(self, package_id: int) -> list[TenantDO]:
        return await self.tenant_mapper.select_list_by_package_id(package_id)

    database: SessionProvider = Inject()
    tenant_context: TenantContext = Inject()
    settings: TenantSettings = Inject()
    passwords: PasswordEncoder = Inject()
    users: AdminUserMapper = Inject()
    roles: RoleMapper = Inject()
    menus: MenuMapper = Inject()
    user_roles: PermissionUserRoleMapper = Inject()
    role_menus: RoleMenuMapper = Inject()
    packages: TenantPackageMapper = Inject()
    authentication: SystemAuthenticationMapper = Inject()
    workloads: SystemWorkloadService = Inject()
    revisions: AuthorizationRevisionService = Inject()

    async def _package(self, package_id):
        package = await self.packages.select_by_id(package_id)
        if package is None:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_NOT_EXISTS)
        if package.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.TENANT_PACKAGE_DISABLE)
        return package

    async def create_tenant(self, create_req_vo):
        await self._valid_tenant_name_duplicate(create_req_vo.name, None)
        for website in create_req_vo.websites or []:
            await self._valid_tenant_website_duplicate(website, None)
        package = await self._package(create_req_vo.package_id)
        identifier = self.database.next_id()
        async with self.workloads.scope("system.tenant.provision", str(identifier)):
            async with self.database.transaction():
                values = create_req_vo.model_dump(
                    exclude={"username", "password", "id"}, by_alias=False
                )
                await self.tenant_mapper.insert(TenantDO(id=identifier, **values))
                role = await self.roles.insert(
                    RoleDO(
                        name=RoleCodeEnum.TENANT_ADMIN.label,
                        code=RoleCodeEnum.TENANT_ADMIN.code,
                        sort=0,
                        builtin=BuiltinTypeEnum.BUILTIN.code,
                        status=StatusEnum.ENABLE.code,
                        data_scope=1,
                        data_scope_dept_ids=[],
                        remark="租户管理员",
                    )
                )
                user = await self.users.insert(
                    AdminUserDO(
                        username=create_req_vo.username,
                        password=await self.passwords.hash(create_req_vo.password),
                        nickname=create_req_vo.contact_name,
                        status=StatusEnum.ENABLE.code,
                        post_ids=[],
                        dept_id=None,
                    )
                )
                await self.user_roles.insert(UserRoleDO(user_id=user.id, role_id=role.id))
                await self.role_menus.insert_batch(
                    [RoleMenuDO(role_id=role.id, menu_id=menu_id) for menu_id in package.menu_ids]
                )
                await self.tenant_mapper.update_by_id(
                    TenantDO(id=identifier, contact_user_id=user.id)
                )
                await self.revisions.advance()
        return identifier

    async def update_tenant(self, update_req_vo):
        tenant = await self._validate_update_tenant(update_req_vo.id)
        await self._valid_tenant_name_duplicate(update_req_vo.name, tenant.id)
        for website in update_req_vo.websites or []:
            await self._valid_tenant_website_duplicate(website, tenant.id)
        package = await self._package(update_req_vo.package_id)
        async with self.workloads.scope("system.tenant.provision", str(tenant.id)):
            async with self.database.transaction():
                values = update_req_vo.model_dump(exclude={"username", "password"}, by_alias=False)
                await self.tenant_mapper.update_by_id(TenantDO(**values))
                if tenant.package_id != update_req_vo.package_id:
                    await self._apply_role_menus(set(package.menu_ids))
                await self.revisions.advance()

    async def update_tenant_role_menu(self, tenant_id, menu_ids):
        async with self.workloads.scope("system.tenant.provision", str(tenant_id)):
            async with self.database.transaction():
                await self._apply_role_menus(menu_ids)
                await self.revisions.advance()

    async def _apply_role_menus(self, menu_ids):
        for role in await self.roles.select_list():
            current = {row.menu_id for row in await self.role_menus.select_list_by_role_id(role.id)}
            wanted = menu_ids if role.code == RoleCodeEnum.TENANT_ADMIN.code else current & menu_ids
            if current - wanted:
                await self.role_menus.delete_list_by_role_id_and_menu_ids(role.id, current - wanted)
            await self.role_menus.insert_batch(
                [RoleMenuDO(role_id=role.id, menu_id=menu_id) for menu_id in wanted - current]
            )

    async def handle_tenant_info(self, handler):
        tenant = await self.get_tenant(int(self.tenant_context.get_required_tenant_id()))
        if tenant is None:
            raise ServiceException(ErrorCodeConstants.TENANT_NOT_EXISTS)
        await handler.handle(tenant)

    async def handle_tenant_menu(self, handler):
        tenant = await self.get_tenant(int(self.tenant_context.get_required_tenant_id()))
        if tenant is None:
            raise ServiceException(ErrorCodeConstants.TENANT_NOT_EXISTS)
        if tenant.package_id == TenantDO.PACKAGE_ID_SYSTEM:
            menu_ids = {menu.id for menu in await self.menus.select_list()}
        else:
            package = await self._package(tenant.package_id)
            menu_ids = set(package.menu_ids)
        await handler.handle(menu_ids)

    async def valid_tenant(self, id):
        tenant = await self.get_tenant(int(id))
        if tenant is None:
            raise ServiceException(ErrorCodeConstants.TENANT_NOT_EXISTS)
        if tenant.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.TENANT_DISABLE, tenant.name)
        if tenant.expire_time is not None and tenant.expire_time <= datetime.now(
            timezone.utc
        ).replace(tzinfo=None):
            raise ServiceException(ErrorCodeConstants.TENANT_EXPIRE, tenant.name)

    async def tenant_info(self, tenant_id):
        result = await self.tenant_mapper.read_from_primary(
            select(TenantDO).where(TenantDO.id == int(tenant_id))
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            return None
        enabled = tenant.status == StatusEnum.ENABLE.code and (
            tenant.expire_time is None
            or tenant.expire_time > datetime.now(timezone.utc).replace(tzinfo=None)
        )
        return TenantInfo(tenant_id=tenant_id, enabled=enabled)

    async def authorize_session(self, identity, policy):
        if (
            identity.realm is not SecurityRealm.TENANT
            or identity.access_mode is not TenantAccessMode.DIRECT_MEMBERSHIP
        ):
            raise SecurityException(SecurityErrorCodes.DENIED, detail="会话类型不支持该操作")
        user = await self.authentication.user_by_id(int(identity.account_id), identity.tenant_id)
        if user is None or str(user.id) != identity.membership_id:
            raise SecurityException(SecurityErrorCodes.CREDENTIALS)
        if user.status != StatusEnum.ENABLE.code:
            raise SecurityException(SecurityErrorCodes.DISABLED)
        if user.credential_revision != identity.credential_revision:
            raise SecurityException(SecurityErrorCodes.CREDENTIALS)
        return None

    async def authorize_workload(self, identity, capability):
        if capability not in WorkloadConstants.RESOURCES:
            raise SecurityException(SecurityErrorCodes.DENIED, detail=f"未登记的能力：{capability}")
        if capability not in identity.capabilities:
            raise SecurityException(
                SecurityErrorCodes.DENIED, detail=f"服务身份缺少该能力：{capability}"
            )
        if identity.tenant_id is None:
            raise SecurityException(SecurityErrorCodes.DENIED, detail="缺少租户上下文")
        return TenantAccessGrant(
            tenant_id=identity.tenant_id,
            source=identity.audience,
            resources=tuple(
                (
                    TenantResourceGrant(resource=resource, actions=actions)
                    for resource, actions in WorkloadConstants.RESOURCES[capability].items()
                )
            ),
            expires_at=identity.expires_at,
            allow_unavailable=capability == "system.tenant.provision",
        )

    async def enabled_tenant_ids(self):
        rows = (
            (
                await self.tenant_mapper.read_from_primary(
                    select(TenantDO).where(TenantDO.status == StatusEnum.ENABLE.code)
                )
            )
            .scalars()
            .all()
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return tuple(
            (str(row.id) for row in rows if row.expire_time is None or row.expire_time > now)
        )
