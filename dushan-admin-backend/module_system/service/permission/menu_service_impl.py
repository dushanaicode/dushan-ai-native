from __future__ import annotations

from collections import defaultdict
from typing import override

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.permission.vo.menu.menu_list_req_vo import MenuListReqVO
from module_system.controller.admin.permission.vo.menu.menu_save_vo import MenuSaveVO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.dal.mapper.permission.menu_mapper import MenuMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)
from module_system.service.permission.menu_service import MenuService
from module_system.service.permission.permission_service import PermissionService
from module_system.service.tenant.handler.menu_filter_handler import MenuListFilterHandler
from module_system.service.tenant.tenant_service import TenantService


@service(interface=MenuService)
class MenuServiceImpl(MenuService):
    revisions: AuthorizationRevisionService = Inject()
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    menu_mapper: MenuMapper = Inject()
    tenant_service: TenantService = Inject()
    permission_service: PermissionService = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_menu(self, create_req_vo: MenuSaveVO) -> int:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.PERMISSION_MENU_ID_LIST),
            required=True,
            name="system-cache",
        )
        await self.validate_parent_menu(create_req_vo.parent_id, None)
        await self.validate_menu(create_req_vo.parent_id, create_req_vo.name, None)
        menu = MenuDO(**create_req_vo.model_dump(by_alias=False))
        self.init_menu_property(menu)
        await self.menu_mapper.insert(menu)
        return menu.id

    @override
    @transactional
    async def update_menu(self, update_req_vo: MenuSaveVO) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.PERMISSION_MENU_ID_LIST),
            required=True,
            name="system-cache",
        )
        existing_menu = await self.menu_mapper.select_by_id(update_req_vo.id)
        if existing_menu is None:
            raise ServiceException(ErrorCodeConstants.MENU_NOT_EXISTS)
        await self.validate_parent_menu(update_req_vo.parent_id, update_req_vo.id)
        await self.validate_menu(update_req_vo.parent_id, update_req_vo.name, update_req_vo.id)
        update_obj = MenuDO(**update_req_vo.model_dump(by_alias=False))
        self.init_menu_property(update_obj)
        await self.menu_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, menu_id: int, status: int) -> None:
        await self.revisions.advance()
        "更新菜单状态"
        menu = await self.menu_mapper.select_by_id(menu_id)
        if menu is None:
            raise ServiceException(ErrorCodeConstants.MENU_NOT_EXISTS)
        update_obj = MenuDO(id=menu_id, status=status)
        await self.menu_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_menu(self, menu_id: int) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.PERMISSION_MENU_ID_LIST),
            required=True,
            name="system-cache",
        )
        count = await self.menu_mapper.select_count_by_parent_id(menu_id)
        if count > 0:
            raise ServiceException(ErrorCodeConstants.MENU_EXISTS_CHILDREN)
        menu = await self.menu_mapper.select_by_id(menu_id)
        if menu is None:
            raise ServiceException(ErrorCodeConstants.MENU_NOT_EXISTS)
        await self.menu_mapper.delete_by_id(menu_id)
        await self.permission_service.process_menu_deleted(menu_id)

    @override
    @transactional
    async def delete_menu_batch(self, menu_ids: list[int]) -> int:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.PERMISSION_MENU_ID_LIST),
            required=True,
            name="system-cache",
        )
        menus = await self.menu_mapper.select_by_ids(menu_ids)
        if len(menus) != len(menu_ids):
            raise ServiceException(ErrorCodeConstants.MENU_NOT_EXISTS)
        if await self.menu_mapper.count(MenuDO.parent_id.in_(menu_ids), MenuDO.id.not_in(menu_ids)):
            raise ServiceException(ErrorCodeConstants.MENU_EXISTS_CHILDREN)
        deleted_count = await self.menu_mapper.delete_by_ids(menu_ids)
        for menu_id in menu_ids:
            await self.permission_service.process_menu_deleted(menu_id)
        return deleted_count

    @override
    async def filter_disable_menus(self, menu_list: list[MenuDO]) -> list[MenuDO]:
        if not menu_list:
            return []
        menu_map: dict[int, MenuDO] = {menu.id: menu for menu in menu_list}
        disabled_cache: set[int] = set()

        def is_menu_disabled(menu: MenuDO) -> bool:
            if menu.id in disabled_cache:
                return True
            if menu.status != StatusEnum.ENABLE.code:
                disabled_cache.add(menu.id)
                return True
            if menu.parent_id in (menu.ID_ROOT, None):
                return False
            parent = menu_map.get(menu.parent_id)
            if parent is None or is_menu_disabled(parent):
                disabled_cache.add(menu.id)
                return True
            return False

        return [menu for menu in menu_list if not is_menu_disabled(menu)]

    @override
    async def get_menu_list_by_tenant(self, req: MenuListReqVO) -> list[MenuDO]:
        all_menus = await self.get_menu_list_by_req(req)
        if not all_menus:
            return []
        menu_filter_handler = MenuListFilterHandler(all_menus)
        await self.tenant_service.handle_tenant_menu(menu_filter_handler)
        return menu_filter_handler.get_filtered_menus()

    @cache(
        SystemCacheKeys.PERMISSION_MENU_ID_LIST,
        key="permission:{{permission}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_menu_id_list_by_permission_from_cache(self, permission: str) -> list[int]:
        menus: list[MenuDO] = await self.menu_mapper.select_list_by_permission(permission)
        return [menu.id for menu in menus] if menus else []

    @override
    async def get_menu(self, menu_id: int) -> MenuDO | None:
        return await self.menu_mapper.select_by_id(menu_id)

    @override
    async def get_menu_list_by_req(self, req: MenuListReqVO | None = None) -> list[MenuDO]:
        return await self.menu_mapper.select_list_by_req(req)

    @override
    async def get_menu_list(self) -> list[MenuDO]:
        return await self.menu_mapper.select_list()

    @override
    async def validate_parent_menu(self, parent_id: int | None, child_id: int | None) -> None:
        if parent_id is None or parent_id == MenuDO.ID_ROOT:
            return
        if child_id is not None and parent_id == child_id:
            raise ServiceException(ErrorCodeConstants.MENU_PARENT_ERROR)
        parent_menu = await self.menu_mapper.select_by_id(parent_id)
        if parent_menu is None:
            raise ServiceException(ErrorCodeConstants.MENU_PARENT_NOT_EXISTS)
        if parent_menu.kind not in ("group", "page"):
            raise ServiceException(ErrorCodeConstants.MENU_PARENT_NOT_DIR_OR_MENU)

    @override
    async def validate_menu(self, parent_id: int | None, name: str, menu_id: int | None) -> None:
        menu = await self.menu_mapper.select_by_parent_id_and_name(parent_id, name)
        if menu is None:
            return
        if menu_id is None or menu.id != menu_id:
            raise ServiceException(ErrorCodeConstants.MENU_NAME_DUPLICATE)

    @override
    def init_menu_property(self, menu: MenuDO) -> None:
        if menu.kind == "action":
            menu.component = ""
            menu.component_name = ""
            menu.icon = ""
            menu.path = ""

    @override
    async def get_menu_list_by_ids(self, ids: set[int]) -> list[MenuDO]:
        return await self.menu_mapper.select_by_ids(ids)

    @cache(
        SystemCacheKeys.PERMISSION_MENU_ID_LIST,
        key="batch-perms:{{permissions}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_menu_ids_by_permissions(self, permissions: set[str]) -> dict[str, list[int]]:
        if not permissions:
            return {}
        menus = await self.menu_mapper.select_list_by_permissions(permissions)
        result: dict[str, list[int]] = defaultdict(list)
        for menu in menus:
            if menu.permission:
                result[menu.permission].append(menu.id)
        return dict(result)
