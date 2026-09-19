from __future__ import annotations

from typing import Any, Collection, override

from framework.common.enums import BuiltinTypeEnum, StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_cache.public import CacheHandler, cache
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    get_bean,
    service,
)
from framework.starter_security.public import (
    BizLogService,
    LogRecordContext,
    LogRecordSpec,
    SecuritySettings,
    log_record,
)
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.permission.vo.role.role_page_req_vo import RolePageReqVO
from module_system.controller.admin.permission.vo.role.role_save_req_vo import RoleSaveReqVO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.permission.dto.role_cache_dto import RoleCacheDTO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.mapper.permission.role_mapper import RoleMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.log_record_constants import LogRecordConstants
from module_system.definitions.enums.permission.permission_data_scope_enum import (
    PermissionDataScopeEnum,
)
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
from module_system.service.permission.role_service import RoleService


@service(interface=RoleService)
class RoleServiceImpl(RoleService):
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    log_context: LogRecordContext = Inject()
    role_mapper: RoleMapper = Inject()
    permission_service: PermissionService = Inject()
    settings: SystemSettings = Inject()
    security_settings: SecuritySettings = Inject()
    revisions: AuthorizationRevisionService = Inject()
    permission_cache: PermissionCacheService = Inject()
    default_ttl: int = 3600

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_ROLE_CREATE_SUB_TYPE,
            biz_no="{{ role.id }}",
            success=LogRecordConstants.SYSTEM_ROLE_CREATE_SUCCESS,
            type=LogRecordConstants.SYSTEM_ROLE_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def create_role(self, create_req_vo: RoleSaveReqVO, builtin: int | None = None) -> int:
        await self.revisions.advance()
        await self.validate_role_duplicate(create_req_vo.name, create_req_vo.code, None)
        role = RoleDO(**create_req_vo.model_dump(by_alias=False))
        role.builtin = builtin if builtin is not None else BuiltinTypeEnum.CUSTOM.code
        role.status = StatusEnum.ENABLE.code
        role.data_scope = PermissionDataScopeEnum.ALL.code
        await self.role_mapper.insert(role)
        await self.permission_cache.invalidate_role_caches()
        if self.security_settings.bizlog_enabled:
            self.log_context.put("role", {"id": role.id, "name": role.name})
        return role.id

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_ROLE_UPDATE_SUB_TYPE,
            biz_no="{{ role.id }}",
            success=LogRecordConstants.SYSTEM_ROLE_UPDATE_SUCCESS,
            type=LogRecordConstants.SYSTEM_ROLE_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def update_role(self, update_req_vo: RoleSaveReqVO) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.ROLE),
            required=True,
            name="system-cache",
        )
        old_role = await self.validate_role_for_update(update_req_vo.id)
        old_role_vo = RoleSaveReqVO(
            id=str(old_role.id),
            name=old_role.name,
            code=old_role.code,
            sort=old_role.sort,
            remark=old_role.remark,
        )
        if self.security_settings.bizlog_enabled:
            await get_bean(BizLogService).record_diff(old_role_vo, update_req_vo)
        await self.validate_role_duplicate(update_req_vo.name, update_req_vo.code, update_req_vo.id)
        role = RoleDO(**update_req_vo.model_dump(by_alias=False))
        await self.role_mapper.update_by_id(role)
        await self.permission_cache.invalidate_role_caches()
        if self.security_settings.bizlog_enabled:
            self.log_context.put("role", {"id": role.id, "name": role.name})

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_ROLE_DELETE_SUB_TYPE,
            biz_no="{{ role.id }}",
            success=LogRecordConstants.SYSTEM_ROLE_DELETE_SUCCESS,
            type=LogRecordConstants.SYSTEM_ROLE_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def delete_role(self, id: int) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.ROLE),
            required=True,
            name="system-cache",
        )
        role = await self.validate_role_for_update(id)
        await self.role_mapper.delete_by_id(id)
        await self.permission_service.process_role_deleted(id)
        await self.permission_cache.invalidate_role_caches()
        if self.security_settings.bizlog_enabled:
            self.log_context.put("role", {"id": role.id, "name": role.name})

    @override
    @transactional
    async def delete_role_batch(self, ids: list[int]) -> int:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.ROLE),
            required=True,
            name="system-cache",
        )
        deleted_count = 0
        for role_id in ids:
            await self.delete_role(role_id)
            deleted_count += 1
        return deleted_count

    async def validate_role_duplicate(self, name: str, code: str, role_id: int | None) -> None:
        if RoleCodeEnum.is_super_admin(code):
            raise ServiceException(ErrorCodeConstants.ROLE_ADMIN_CODE_ERROR, code)
        role_by_name = await self.role_mapper.select_by_name(name)
        if role_by_name is not None and (role_id is None or role_by_name.id != role_id):
            raise ServiceException(ErrorCodeConstants.ROLE_NAME_DUPLICATE, name)
        if code and code.strip():
            role_by_code = await self.role_mapper.select_by_code(code)
            if role_by_code is not None and (role_id is None or role_by_code.id != role_id):
                raise ServiceException(ErrorCodeConstants.ROLE_CODE_DUPLICATE, code)

    async def validate_role_for_update(self, role_id: int) -> Any:
        role = await self.role_mapper.select_by_id(role_id)
        if role is None:
            raise ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
        allow_modify = self.settings.allow_modify_system_role
        if not allow_modify and role.builtin == BuiltinTypeEnum.BUILTIN.code:
            raise ServiceException(ErrorCodeConstants.ROLE_CAN_NOT_UPDATE_SYSTEM_TYPE_ROLE)
        return role

    @override
    async def get_role(self, role_id: int) -> Any:
        return await self.role_mapper.select_by_id(role_id)

    @cache(
        SystemCacheKeys.ROLE,
        key="id:{{role_id}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_role_from_cache(self, role_id: int) -> RoleCacheDTO | None:
        loaded = await self.role_mapper.select_by_id(role_id)
        return None if loaded is None else RoleCacheDTO.model_validate(loaded)

    @override
    async def get_role_list_by_status(self, statuses: Collection[int]) -> list[RoleDO]:
        return await self.role_mapper.select_list_by_status(statuses)

    @override
    async def get_role_list_by_ids(self, ids: Collection[int]) -> list[RoleDO]:
        if not ids:
            return []
        return await self.role_mapper.select_by_ids(ids)

    @override
    async def get_role_list_from_cache(self, ids: Collection[int]) -> list[RoleDO]:
        if not ids:
            return []
        roles = [await self.get_role_from_cache(rid) for rid in ids]
        return [role for role in roles if role is not None]

    @override
    async def get_role_page(self, req_vo: RolePageReqVO) -> PageResult[RoleDO]:
        return await self.role_mapper.select_page(req_vo)

    @override
    async def validate_role_list(self, ids: Collection[int]) -> None:
        if not ids:
            return
        roles = await self.role_mapper.select_by_ids(ids)
        role_map = {role.id: role for role in roles}
        for rid in ids:
            role = role_map.get(rid)
            if role is None:
                raise ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
            if role.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.ROLE_IS_DISABLE, role.name)

    @override
    @transactional
    async def update_role_data_scope(
        self, role_id: int, data_scope: int, data_scope_dept_ids: set[int]
    ) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.ROLE),
            required=True,
            name="system-cache",
        )
        role = await self.validate_role_for_update(role_id)
        role.data_scope = data_scope
        role.data_scope_dept_ids = (
            list(data_scope_dept_ids) if data_scope_dept_ids is not None else []
        )
        await self.role_mapper.update_by_id(role)
        await self.permission_cache.invalidate_role_caches()

    @override
    async def has_any_super_admin(self, ids: Collection[int]) -> bool:
        if not ids:
            return False
        roles = await self.get_role_list_from_cache(ids)
        return any((r.code and RoleCodeEnum.is_super_admin(r.code) for r in roles))

    @override
    async def get_role_list(self) -> list[RoleDO]:
        return await self.role_mapper.select_list()

    @override
    @transactional
    async def update_role_status(self, id: int, status: int) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.ROLE),
            required=True,
            name="system-cache",
        )
        await self.validate_role_for_update(id)
        update_obj = RoleDO(id=id, status=status)
        await self.role_mapper.update_by_id(update_obj)
        await self.permission_cache.invalidate_role_caches()
