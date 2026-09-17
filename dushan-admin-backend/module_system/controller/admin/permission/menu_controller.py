from operator import attrgetter

from fastapi import APIRouter, Depends, Query

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.permission.vo.menu.menu_list_req_vo import MenuListReqVO
from module_system.controller.admin.permission.vo.menu.menu_resp_vo import MenuRespVO
from module_system.controller.admin.permission.vo.menu.menu_save_vo import MenuSaveVO
from module_system.controller.admin.permission.vo.menu.menu_simple_resp_vo import MenuSimpleRespVO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.definitions.vo.update_status_req_vo import UpdateStatusReqVO
from module_system.service.permission.menu_service import MenuService

menu_controller = APIRouter(prefix="/permission/menu", tags=["System - 菜单管理"])


class MenuController:
    @staticmethod
    @menu_controller.post("/create", summary="创建菜单")
    @RoutePolicy(
        permissions=("system:permission:menu:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_menu(
        create_req_vo: MenuSaveVO,
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[SnowflakeIdStr]:
        id = await menu_service.create_menu(create_req_vo)
        return Result.success(data=id)

    @staticmethod
    @menu_controller.put("/update", summary="修改菜单")
    @RoutePolicy(
        permissions=("system:permission:menu:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_menu(
        update_req_vo: MenuSaveVO,
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[bool]:
        await menu_service.update_menu(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @menu_controller.put("/update-status", summary="修改菜单状态")
    @RoutePolicy(
        permissions=("system:permission:menu:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @menu_controller.delete("/delete", summary="删除菜单")
    @RoutePolicy(
        permissions=("system:permission:menu:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_menu(
        req_vo: IdReqVO = Query(),
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[bool]:
        await menu_service.delete_menu(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @menu_controller.delete("/delete-list", summary="批量删除菜单")
    @RoutePolicy(
        permissions=("system:permission:menu:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_menu_batch(
        req_vo: IdListReqVO = Query(),
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[int]:
        deleted_count = await menu_service.delete_menu_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @menu_controller.get("/list", summary="获取菜单列表")
    @RoutePolicy(
        permissions=("system:permission:menu:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_menu_list(
        req_vo: MenuListReqVO = Query(),
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[list[MenuRespVO]]:
        menus = await menu_service.get_menu_list_by_req(req_vo)
        menus.sort(key=attrgetter("sort"))
        resp_list = [MenuRespVO.model_validate(m) for m in menus]
        return Result.success(data=resp_list)

    @staticmethod
    @menu_controller.get("/simple-list", summary="获取菜单精简信息列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_menu_simple_list(
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[list[MenuSimpleRespVO]]:
        req = MenuListReqVO(status=StatusEnum.ENABLE.code)
        menus = await menu_service.get_menu_list_by_tenant(req)
        menus = await menu_service.filter_disable_menus(menus)
        menus.sort(key=attrgetter("sort"))
        resp_list = [MenuSimpleRespVO.model_validate(m) for m in menus]
        return Result.success(data=resp_list)

    @staticmethod
    @menu_controller.get("/get", summary="获取菜单信息")
    @RoutePolicy(
        permissions=("system:permission:menu:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_menu(
        req_vo: IdReqVO = Query(),
        menu_service: MenuService = Depends(DiDependency(MenuService)),
    ) -> Result[MenuRespVO]:
        menu = await menu_service.get_menu(req_vo.id)
        resp = MenuRespVO.model_validate(menu) if menu else None
        return Result.success(data=resp)
