from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import StatusEnum
from framework.common.page import PageResult
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.common.utils import ConversionUtils
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_excel.public import (
    ExcelWriter,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    AccessLogPolicy,
    FileResult,
    Result,
    RoutePolicy,
)
from module_system.controller.admin.tenant.vo.tenant.tenant_export_req_vo import TenantExportReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_name_req_vo import TenantNameReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_resp_vo import TenantRespVO
from module_system.controller.admin.tenant.vo.tenant.tenant_save_req_vo import TenantSaveReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_simple_resp_vo import TenantSimpleRespVO
from module_system.controller.admin.tenant.vo.tenant.tenant_update_req_vo import TenantUpdateReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_website_req_vo import TenantWebsiteReqVO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.service.tenant.tenant_service import TenantService

tenant_controller = APIRouter(prefix="/tenant", tags=["System - 租户管理"])


class TenantController:
    @staticmethod
    @tenant_controller.get("/get-id-by-name", summary="使用租户名，获得租户编号")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT, roles=("super_admin",))
    @AccessLogPolicy(enabled=False)
    async def get_tenant_id_by_name(
        req_vo: TenantNameReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[int | None]:
        tenant = await tenant_service.get_tenant_by_name(req_vo.name)
        tenant_id = tenant.id if tenant else None
        return Result.success(data=tenant_id)

    @staticmethod
    @tenant_controller.get(
        "/simple-list",
        summary="获取租户精简信息列表",
        description="只包含被开启的租户，用于【首页】功能的选择租户选项",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT, roles=("super_admin",))
    @AccessLogPolicy(enabled=False)
    async def get_tenant_simple_list(
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[list[TenantSimpleRespVO]]:
        tenant_list: list[TenantDO] = await tenant_service.get_tenant_list_by_status(
            StatusEnum.ENABLE.code
        )
        response = [TenantSimpleRespVO.model_validate(tenant) for tenant in tenant_list]
        return Result.success(data=response)

    @staticmethod
    @tenant_controller.get("/get-by-website", summary="获取租户")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT, roles=("super_admin",))
    @AccessLogPolicy(enabled=False)
    async def get_tenant_by_website(
        req_vo: TenantWebsiteReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[TenantSimpleRespVO]:
        tenant = await tenant_service.get_tenant_by_website(req_vo.website)
        data = TenantSimpleRespVO.model_validate(tenant) if tenant else None
        return Result.success(data=data)

    @staticmethod
    @tenant_controller.post("/create", summary="创建租户")
    @RoutePolicy(
        permissions=("system:tenant:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def create_tenant(
        create_req_vo: TenantSaveReqVO,
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[SnowflakeIdStr]:
        tenant_id = await tenant_service.create_tenant(create_req_vo)
        return Result.success(data=tenant_id)

    @staticmethod
    @tenant_controller.put("/update", summary="更新租户")
    @RoutePolicy(
        permissions=("system:tenant:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def update_tenant(
        update_req_vo: TenantUpdateReqVO,
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[bool]:
        await tenant_service.update_tenant(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @tenant_controller.put("/update-status", summary="修改租户状态")
    @RoutePolicy(
        permissions=("system:tenant:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def update_status(
        req_vo: UpdateStatusReqVO, service: TenantService = Depends(DiDependency(TenantService))
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @tenant_controller.delete("/delete", summary="删除租户")
    @RoutePolicy(
        permissions=("system:tenant:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def delete_tenant(
        req_vo: IdReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[bool]:
        await tenant_service.delete_tenant(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @tenant_controller.delete("/delete-list", summary="批量删除租户")
    @RoutePolicy(
        permissions=("system:tenant:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def delete_tenant_batch(
        req_vo: IdListReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[int]:
        deleted_count = await tenant_service.delete_tenant_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @tenant_controller.get("/get", summary="获得租户")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT, roles=("super_admin",))
    async def get_tenant(
        req_vo: IdReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[TenantRespVO]:
        tenant = await tenant_service.get_tenant(req_vo.id)
        data = TenantRespVO.model_validate(tenant) if tenant else None
        return Result.success(data=data)

    @staticmethod
    @tenant_controller.get("/page", summary="获得租户分页")
    @RoutePolicy(
        permissions=("system:tenant:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def get_tenant_page(
        page_req_vo: TenantPageReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
    ) -> Result[PageResult[TenantRespVO]]:
        page_result: PageResult[TenantDO] = await tenant_service.get_tenant_page(page_req_vo)
        resp_vo: PageResult[TenantRespVO] = page_result.convert(TenantRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @tenant_controller.get("/export-fields", summary="获取租户可导出字段列表")
    @RoutePolicy(
        permissions=("system:tenant:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def get_export_tenant_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(TenantRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @tenant_controller.get(
        "/export-excel", summary="导出租户 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:tenant:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
        roles=("super_admin",),
    )
    async def export_tenant_excel(
        page_req_vo: TenantExportReqVO = Query(),
        tenant_service: TenantService = Depends(DiDependency(TenantService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> StreamingResponse:
        excel_writer.prepare_export_query(page_req_vo)
        page_result: PageResult[TenantDO] = await tenant_service.get_tenant_page(page_req_vo)
        excel_list: list[TenantRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, TenantRespVO
        )
        filename = "租户数据"
        file_data = await excel_writer.write(
            "数据", TenantRespVO, excel_list, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
