from fastapi import APIRouter, Body, Depends, Query

from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.permission.vo.permission.permission_assign_role_data_scope_req_vo import (
    PermissionAssignRoleDataScopeReqVO,
)
from module_system.controller.admin.permission.vo.permission.permission_assign_role_menu_req_vo import (
    PermissionAssignRoleMenuReqVO,
)
from module_system.controller.admin.permission.vo.permission.permission_assign_user_role_req_vo import (
    PermissionAssignUserRoleReqVO,
)
from module_system.controller.admin.permission.vo.permission.permission_user_role_req_vo import (
    PermissionUserRoleReqVO,
)
from module_system.controller.admin.permission.vo.permission.role_ids_req_vo import RoleIdsReqVO
from module_system.controller.admin.permission.vo.permission.role_menu_req_vo import (
    RoleMenuReqVO,
)
from module_system.service.permission.permission_service import PermissionService
from module_system.service.tenant.handler.role_menu_id_filter_handler import RoleMenuIdFilterHandler
from module_system.service.tenant.tenant_service import TenantService

permission_controller = APIRouter(prefix="/permission", tags=["System - 权限管理"])


class PermissionController:
    @staticmethod
    @permission_controller.get("/list-role-menus", summary="获得角色拥有的菜单编号")
    @RoutePolicy(
        permissions=("system:permission:assign-role-menu",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_role_menu_list(
        req_vo: RoleMenuReqVO = Query(),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[set[int]]:
        menu_ids = await permission_service.get_role_menu_list_by_role_id(req_vo.role_id)
        return Result.success(data=menu_ids)

    @staticmethod
    @permission_controller.get("/list-role-menus-by-ids", summary="获得多个角色拥有的菜单编号")
    @RoutePolicy(
        permissions=("system:permission:assign-role-menu",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_role_menu_list_by_ids(
        req_vo: RoleIdsReqVO = Query(),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[set[int]]:
        role_ids = req_vo.role_ids
        menu_ids = await permission_service.get_role_menu_list_by_role_ids(set(role_ids))
        return Result.success(data=menu_ids)

    @staticmethod
    @permission_controller.post("/assign-role-menu", summary="赋予角色菜单")
    @RoutePolicy(
        permissions=("system:permission:assign-role-menu",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def assign_role_menu(
        req_vo: PermissionAssignRoleMenuReqVO = Body(...),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[bool]:
        id_filter_handler = RoleMenuIdFilterHandler(req_vo.menu_ids)
        await tenant_service.handle_tenant_menu(id_filter_handler)
        filtered_menu_ids = id_filter_handler.get_filtered_ids()
        await permission_service.assign_role_menu(req_vo.role_id, filtered_menu_ids)
        return Result.success(data=True)

    @staticmethod
    @permission_controller.post("/assign-role-data-scope", summary="赋予角色数据权限")
    @RoutePolicy(
        permissions=("system:permission:assign-role-data-scope",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def assign_role_data_scope(
        req_vo: PermissionAssignRoleDataScopeReqVO = Body(...),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[bool]:
        await permission_service.assign_role_data_scope(req_vo)
        return Result.success(data=True)

    @staticmethod
    @permission_controller.get("/list-user-roles", summary="获得管理员拥有的角色编号列表")
    @RoutePolicy(
        permissions=("system:permission:assign-user-role",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def list_admin_roles(
        req_vo: PermissionUserRoleReqVO = Query(),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[set[int]]:
        role_ids = await permission_service.get_user_role_id_list_by_user_id(req_vo.user_id)
        return Result.success(data=role_ids)

    @staticmethod
    @permission_controller.post("/assign-user-role", summary="赋予用户角色")
    @RoutePolicy(
        permissions=("system:permission:assign-user-role",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def assign_user_role(
        req_vo: PermissionAssignUserRoleReqVO = Body(...),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
    ) -> Result[bool]:
        await permission_service.assign_user_role(req_vo.user_id, req_vo.role_ids)
        return Result.success(data=True)
