from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.enums.builtin_type_enum import BuiltinTypeEnum
from framework.common.enums.status_enum import StatusEnum
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.common.utils.collection.conversion_utils import ConversionUtils
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.permission.vo.role.role_export_req_vo import RoleExportReqVO
from module_system.controller.admin.permission.vo.role.role_page_req_vo import RolePageReqVO
from module_system.controller.admin.permission.vo.role.role_resp_vo import RoleRespVO
from module_system.controller.admin.permission.vo.role.role_save_req_vo import RoleSaveReqVO
from module_system.controller.admin.permission.vo.role.role_update_status_req_vo import (
    RoleUpdateStatusReqVO,
)
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.dept.dept_service import DeptService
from module_system.service.permission.role_service import RoleService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

role_controller = APIRouter(prefix="/permission/role", tags=["System - 角色管理"])


class RoleController:
    @staticmethod
    @role_controller.post("/create", summary="创建角色")
    @RoutePolicy(
        permissions=("system:permission:role:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_role(
        create_req_vo: RoleSaveReqVO,
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[SnowflakeIdStr]:
        builtin = BuiltinTypeEnum.CUSTOM.code
        role_id = await role_service.create_role(create_req_vo, builtin)
        return Result.success(data=role_id)

    @staticmethod
    @role_controller.put("/update", summary="更新角色")
    @RoutePolicy(
        permissions=("system:permission:role:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_role(
        update_req_vo: RoleSaveReqVO,
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[bool]:
        await role_service.update_role(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @role_controller.put("/update-status", summary="修改角色状态")
    @RoutePolicy(
        permissions=("system:permission:role:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_role_status(
        req_vo: RoleUpdateStatusReqVO,
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[bool]:
        await role_service.update_role_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @role_controller.delete("/delete", summary="删除角色")
    @RoutePolicy(
        permissions=("system:permission:role:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_role(
        req_vo: IdReqVO = Query(),
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[bool]:
        await role_service.delete_role(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @role_controller.delete("/delete-list", summary="批量删除角色")
    @RoutePolicy(
        permissions=("system:permission:role:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_role_batch(
        req_vo: IdListReqVO = Query(),
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[int]:
        deleted_count = await role_service.delete_role_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @role_controller.get("/get", summary="获得角色")
    @RoutePolicy(
        permissions=("system:permission:role:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_role(
        req_vo: IdReqVO = Query(),
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[RoleRespVO]:
        role = await role_service.get_role(req_vo.id)
        data = RoleRespVO.model_validate(role) if role else None
        return Result.success(data=data)

    @staticmethod
    @role_controller.get("/page", summary="获得角色分页")
    @RoutePolicy(
        permissions=("system:permission:role:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_role_page(
        page_vo: RolePageReqVO = Query(),
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[PageResult[RoleRespVO]]:
        page_result: PageResult[RoleDO] = await role_service.get_role_page(page_vo)
        resp_vo: PageResult[RoleRespVO] = page_result.convert(RoleRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @role_controller.get("/simple-list", summary="获取角色精简信息列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_role_list(
        role_service: RoleService = Depends(DiDependency(RoleService)),
    ) -> Result[list[RoleRespVO]]:
        roles = await role_service.get_role_list_by_status([StatusEnum.ENABLE.code])
        roles.sort(key=lambda r: r.sort)
        data = [RoleRespVO.model_validate(role) for role in roles]
        return Result.success(data=data)

    @staticmethod
    @role_controller.get("/export-fields", summary="获取角色可导出字段列表")
    @RoutePolicy(
        permissions=("system:permission:role:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_role_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(RoleRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @role_controller.get(
        "/export-excel", summary="导出角色 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:permission:role:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_roles_excel(
        page_req_vo: RoleExportReqVO = Query(),
        role_service: RoleService = Depends(DiDependency(RoleService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
        departments: DeptInfoProviderAdapter = Depends(DiDependency(DeptInfoProviderAdapter)),
        posts: PostInfoProviderAdapter = Depends(DiDependency(PostInfoProviderAdapter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(
            dictionaries=dictionaries, departments=departments, posts=posts
        )
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[RoleDO] = await role_service.get_role_page(page_req_vo)
        excel_list: list[RoleRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, RoleRespVO
        )
        filename = "角色数据"
        file_data = await excel_writer.write(
            "数据", RoleRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
