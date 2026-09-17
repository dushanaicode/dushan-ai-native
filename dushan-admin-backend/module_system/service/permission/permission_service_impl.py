from __future__ import annotations

from sqlalchemy import select

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_data_permission.enums.data_scope import DataScope
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_tenant.context.tenant_context import TenantContext
from module_system.api.permission.dto.dept_data_permission_resp_dto import DeptDataPermissionRespDTO
from module_system.controller.admin.permission.vo.permission.permission_assign_role_data_scope_req_vo import (
    PermissionAssignRoleDataScopeReqVO,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO
from module_system.dal.dataobject.permission.authorization_revision_do import (
    AuthorizationRevisionDO,
)
from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.dal.dataobject.permission.permission_user_role_do import UserRoleDO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.permission.role_menu_do import RoleMenuDO
from module_system.dal.mapper.auth.system_authentication_mapper import SystemAuthenticationMapper
from module_system.dal.mapper.dept.dept_mapper import DeptMapper
from module_system.dal.mapper.permission.menu_mapper import MenuMapper
from module_system.dal.mapper.permission.permission_user_role_mapper import PermissionUserRoleMapper
from module_system.dal.mapper.permission.role_mapper import RoleMapper
from module_system.dal.mapper.permission.role_menu_mapper import RoleMenuMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.permission.role_code_enum import (
    RoleCodeEnum,
)
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)
from module_system.service.permission.permission_cache_service import (
    PermissionCacheService,
)
from module_system.service.permission.permission_service import PermissionService


@service(interface=PermissionService)
class PermissionServiceImpl(PermissionService):
    database: SessionProvider = Inject()
    role_menu_mapper: RoleMenuMapper = Inject()
    user_role_mapper: PermissionUserRoleMapper = Inject()
    roles: RoleMapper = Inject()
    menus: MenuMapper = Inject()
    users: AdminUserMapper = Inject()
    departments: DeptMapper = Inject()
    authentication: SystemAuthenticationMapper = Inject()
    revisions: AuthorizationRevisionService = Inject()
    events: PermissionCacheService = Inject()
    tenant: TenantContext = Inject()
    security: SecurityContext = Inject()

    async def _roles(self, user_id):
        result = await self.roles.read_from_primary(
            select(RoleDO)
            .join(UserRoleDO, RoleDO.id == UserRoleDO.role_id)
            .where(UserRoleDO.user_id == user_id, RoleDO.status == StatusEnum.ENABLE.code)
        )
        return list(result.scalars().all())

    @staticmethod
    def _super(roles):
        return any(role.code == RoleCodeEnum.SUPER_ADMIN.code for role in roles)

    async def has_any_permissions(self, user_id: int, *permissions: str) -> bool:
        if not permissions:
            return True
        roles = await self._roles(user_id)
        if self._super(roles):
            return True
        ids = await self.get_role_menu_list_by_role_ids({role.id for role in roles})
        menus = await self.menus.select_by_ids(ids)
        return any(
            menu.permission in permissions and menu.status == StatusEnum.ENABLE.code
            for menu in menus
        )

    async def has_any_permission(self, roles, permission: str) -> bool:
        if self._super(roles):
            return True
        ids = await self.get_role_menu_list_by_role_ids({role.id for role in roles})
        return any(
            menu.permission == permission and menu.status == StatusEnum.ENABLE.code
            for menu in await self.menus.select_by_ids(ids)
        )

    async def has_any_roles(self, user_id: int, *roles: str) -> bool:
        return not roles or bool(set(roles) & {role.code for role in await self._roles(user_id)})

    async def get_role_menu_list_by_role_id(self, role_id: int) -> set[int]:
        return await self.get_role_menu_list_by_role_ids({role_id})

    async def get_role_menu_list_by_role_ids(self, role_ids) -> set[int]:
        roles = await self.roles.select_by_ids(role_ids)
        if self._super(roles):
            return {menu.id for menu in await self.menus.select_list()}
        return {
            row.menu_id for row in await self.role_menu_mapper.select_list_by_role_ids(role_ids)
        }

    @cache(SystemCacheKeys.MENU_ROLE_ID_LIST, key="{{menu_id}}", ttl_seconds=3600)
    async def get_menu_role_id_list_by_menu_id_from_cache(self, menu_id: int) -> set[int]:
        return {row.role_id for row in await self.role_menu_mapper.select_list_by_menu_id(menu_id)}

    @transactional
    async def assign_user_role(self, user_id: int, role_ids: set[int]) -> None:
        if await self.users.select_by_id(user_id) is None:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        if len(await self.roles.select_by_ids(role_ids)) != len(role_ids):
            raise ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
        current = await self.get_user_role_id_list_by_user_id(user_id)
        for role_id in role_ids - current:
            await self.user_role_mapper.insert(UserRoleDO(user_id=user_id, role_id=role_id))
        if current - role_ids:
            await self.user_role_mapper.delete_list_by_user_id_and_role_ids(
                user_id, current - role_ids
            )
        await self.revisions.advance()
        await self.events.invalidate_user_caches()

    async def get_user_role_id_list_by_user_id(self, user_id: int) -> set[int]:
        return {row.role_id for row in await self.user_role_mapper.select_list_by_user_id(user_id)}

    @cache(SystemCacheKeys.USER_ROLE_ID_LIST, key="{{user_id}}", ttl_seconds=3600)
    async def get_user_role_id_list_by_user_id_from_cache(self, user_id: int) -> set[int]:
        return await self.get_user_role_id_list_by_user_id(user_id)

    async def get_enable_user_role_list_by_user_id_from_cache(self, user_id: int):
        ids = await self.get_user_role_id_list_by_user_id_from_cache(user_id)
        return [
            role
            for role in await self.roles.select_by_ids(ids)
            if role.status == StatusEnum.ENABLE.code
        ]

    @transactional
    async def assign_role_data_scope(self, req: PermissionAssignRoleDataScopeReqVO) -> None:
        scope = DataScope.from_code(req.data_scope)
        if await self.roles.select_by_id(req.role_id) is None:
            raise ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
        if scope is DataScope.DEPT_CUSTOM and len(
            await self.departments.select_by_ids(req.data_scope_dept_ids)
        ) != len(req.data_scope_dept_ids):
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
        await self.roles.update_by_id(
            RoleDO(
                id=req.role_id,
                data_scope=scope.code,
                data_scope_dept_ids=sorted(req.data_scope_dept_ids)
                if scope is DataScope.DEPT_CUSTOM
                else [],
            )
        )
        await self.revisions.advance()
        await self.events.invalidate_role_caches()

    async def get_dept_data_permission(self, user_id: int) -> DeptDataPermissionRespDTO:
        identity = self.security.require()
        if identity.account_id != str(user_id):
            raise SecurityException("denied")
        rules = await self.data_rules(identity)
        result = DeptDataPermissionRespDTO(user_ids={user_id})
        for rule in rules:
            if rule.scope is DataScope.ALL:
                result.all = True
            elif rule.scope is DataScope.SELF:
                result.self_only = True
            elif rule.scope is DataScope.DEPT_CUSTOM:
                result.dept_ids.update(int(value) for value in rule.department_ids)
            elif identity.dept_id is not None:
                result.dept_ids.add(int(identity.dept_id))
                if rule.scope is DataScope.DEPT_AND_CHILD:
                    result.dept_ids.update(
                        int(value)
                        for value in await self.department_descendants(identity, identity.dept_id)
                    )
        if result.dept_ids:
            result.user_ids.update(
                int(value)
                for value in await self.department_memberships(
                    identity, frozenset(str(value) for value in result.dept_ids)
                )
            )
        return result

    @transactional
    async def assign_role_menu(self, role_id: int, menu_ids: set[int]) -> None:
        if await self.roles.select_by_id(role_id) is None:
            raise ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
        if len(await self.menus.select_by_ids(menu_ids)) != len(menu_ids):
            raise ServiceException(ErrorCodeConstants.MENU_NOT_EXISTS)
        current = {
            row.menu_id for row in await self.role_menu_mapper.select_list_by_role_id(role_id)
        }
        for menu_id in menu_ids - current:
            await self.role_menu_mapper.insert(RoleMenuDO(role_id=role_id, menu_id=menu_id))
        if current - menu_ids:
            await self.role_menu_mapper.delete_list_by_role_id_and_menu_ids(
                role_id, current - menu_ids
            )
        await self.revisions.advance()
        await self.events.invalidate_all()

    @transactional
    async def process_menu_deleted(self, menu_id: int) -> None:
        await self.role_menu_mapper.delete_list_by_menu_id(menu_id)
        await self.revisions.advance()
        await self.events.invalidate_menu_caches()

    @transactional
    async def process_role_deleted(self, role_id: int) -> None:
        await self.role_menu_mapper.delete_list_by_role_id(role_id)
        await self.user_role_mapper.delete_list_by_role_id(role_id)
        await self.revisions.advance()
        await self.events.invalidate_role_caches()

    @transactional
    async def process_user_deleted(self, user_id: int) -> None:
        await self.user_role_mapper.delete_list_by_user_id(user_id)
        await self.revisions.advance()
        await self.events.invalidate_user_caches()

    async def get_user_role_id_list_by_role_id(self, role_ids) -> set[int]:
        return {
            row.user_id for row in await self.user_role_mapper.select_list_by_role_ids(role_ids)
        }

    @cache(SystemCacheKeys.USER_MENU_LIST, key="{{user_id}}", ttl_seconds=3600)
    async def get_user_menu_list_by_user_id_from_cache(self, user_id: int) -> set[int]:
        return await self.get_role_menu_list_by_role_ids(
            await self.get_user_role_id_list_by_user_id(user_id)
        )

    async def authorization_revision(self, session) -> str:
        if session.realm is SecurityRealm.ACCOUNT:
            async with self.database.read_session(force_primary=True) as db:
                client = (
                    await db.execute(
                        select(OAuth2ClientDO).where(
                            OAuth2ClientDO.id == int(session.account_id.removeprefix("client:"))
                        )
                    )
                ).scalar_one()
                version = (
                    await db.execute(
                        select(AuthorizationRevisionDO.revision).where(
                            AuthorizationRevisionDO.id == 1
                        )
                    )
                ).scalar_one()
                return f"{version}:{client.credential_revision}"
        return await self.authentication.authorization_revision(
            int(session.account_id), session.tenant_id
        )

    async def _check_revision(self, session):
        if await self.authorization_revision(session) != session.authorization_revision:
            raise SecurityException("credentials")

    async def permission_snapshot(self, session, *, binding: str) -> PermissionSnapshot:
        await self._check_revision(session)
        if session.realm is SecurityRealm.ACCOUNT:
            async with self.database.read_session(force_primary=True) as db:
                client = (
                    await db.execute(
                        select(OAuth2ClientDO).where(
                            OAuth2ClientDO.id == int(session.account_id.removeprefix("client:"))
                        )
                    )
                ).scalar_one()
                permissions, roles = frozenset(client.authorities or []), frozenset()
        else:
            role_list = await self._roles(int(session.account_id))
            roles = frozenset(role.code for role in role_list)
            if self._super(role_list):
                permissions = frozenset({"*:*:*"})
            else:
                statement = (
                    select(MenuDO)
                    .join(RoleMenuDO, MenuDO.id == RoleMenuDO.menu_id)
                    .where(
                        RoleMenuDO.role_id.in_([role.id for role in role_list]),
                        MenuDO.status == StatusEnum.ENABLE.code,
                    )
                )
                menus = (await self.menus.read_from_primary(statement)).scalars().all()
                permissions = frozenset(menu.permission for menu in menus if menu.permission)
        await self._check_revision(session)
        return PermissionSnapshot(
            binding=binding,
            revision=session.authorization_revision,
            permissions=permissions,
            roles=roles,
        )

    async def data_rules(self, session) -> tuple[DataScopeRule, ...]:
        await self._check_revision(session)
        roles = await self._roles(int(session.account_id))
        rules = tuple(
            DataScopeRule(
                scope=DataScope.from_code(role.data_scope),
                department_ids=frozenset(str(value) for value in role.data_scope_dept_ids)
                if role.data_scope == DataScope.DEPT_CUSTOM.code
                else frozenset(),
            )
            for role in roles
        )
        await self._check_revision(session)
        return rules if rules else (DataScopeRule(scope=DataScope.SELF),)

    async def department_descendants(self, session, department_id: str) -> frozenset[str]:
        await self._check_revision(session)
        root = int(department_id)
        if (
            await self.departments.read_from_primary(select(DeptDO.id).where(DeptDO.id == root))
        ).scalar_one_or_none() is None:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
        seen, pending = {root}, [root]
        while pending:
            children = list(
                (
                    await self.departments.read_from_primary(
                        select(DeptDO.id).where(DeptDO.parent_id.in_(pending))
                    )
                ).scalars()
            )
            if seen.intersection(children):
                raise ValueError("部门层级存在循环")
            seen.update(children)
            pending = children
        await self._check_revision(session)
        return frozenset(str(value) for value in seen - {root})

    async def department_memberships(
        self, session, department_ids: frozenset[str]
    ) -> frozenset[str]:
        await self._check_revision(session)
        ids = {int(value) for value in department_ids}
        existing = set(
            (
                await self.departments.read_from_primary(
                    select(DeptDO.id).where(DeptDO.id.in_(ids))
                )
            ).scalars()
        )
        if existing != ids:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
        result = await self.authentication.department_members(session.tenant_id, ids)
        await self._check_revision(session)
        return result
