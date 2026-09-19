from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import StatusEnum
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_excel.public import (
    DictDataProvider,
    ExcelProviders,
    ExcelWriter,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    FileResult,
    Result,
    RoutePolicy,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_export_req_vo import (
    TenantPackageExportReqVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_resp_vo import (
    TenantPackageRespVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_save_req_vo import (
    TenantPackageSaveReqVO,
)
from module_system.controller.admin.tenant.vo.packages.packages_package_simple_resp_vo import (
    TenantPackageSimpleRespVO,
)
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO
from module_system.service.tenant.tenant_package_service import TenantPackageService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

tenant_package_controller = APIRouter(prefix="/tenant/package", tags=["System - 租户套餐管理"])


class TenantPackageController:
    @staticmethod
    @tenant_package_controller.post("/create", summary="创建租户套餐")
    @RoutePolicy(
        permissions=("system:tenant:package:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_tenant_package(
        create_req_vo: TenantPackageSaveReqVO,
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[SnowflakeIdStr]:
        tenant_package_id = await tenant_package_service.create_tenant_package(create_req_vo)
        return Result.success(data=tenant_package_id)

    @staticmethod
    @tenant_package_controller.put("/update", summary="更新租户套餐")
    @RoutePolicy(
        permissions=("system:tenant:package:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_tenant_package(
        update_req_vo: TenantPackageSaveReqVO,
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[bool]:
        await tenant_package_service.update_tenant_package(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @tenant_package_controller.put("/update-status", summary="修改租户套餐状态")
    @RoutePolicy(
        permissions=("system:tenant:package:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @tenant_package_controller.delete("/delete", summary="删除租户套餐")
    @RoutePolicy(
        permissions=("system:tenant:package:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_tenant_package(
        req_vo: IdReqVO = Query(),
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[bool]:
        await tenant_package_service.delete_tenant_package(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @tenant_package_controller.delete("/delete-list", summary="批量删除租户套餐")
    @RoutePolicy(
        permissions=("system:tenant:package:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_tenant_package_batch(
        req_vo: IdListReqVO = Query(),
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[int]:
        deleted_count = await tenant_package_service.delete_tenant_package_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @tenant_package_controller.get("/get", summary="获得租户套餐")
    @RoutePolicy(
        permissions=("system:tenant:package:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_tenant_package(
        req_vo: IdReqVO = Query(),
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[TenantPackageRespVO]:
        tenant_package = await tenant_package_service.get_tenant_package(req_vo.id)
        resp_vo = TenantPackageRespVO.model_validate(tenant_package) if tenant_package else None
        return Result.success(data=resp_vo)

    @staticmethod
    @tenant_package_controller.get("/page", summary="获得租户套餐分页")
    @RoutePolicy(
        permissions=("system:tenant:package:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_tenant_package_page(
        page_req_vo: TenantPackagePageReqVO = Query(),
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[PageResult[TenantPackageRespVO]]:
        page_result: PageResult[
            TenantPackageDO
        ] = await tenant_package_service.get_tenant_package_page(page_req_vo)
        resp_vo: PageResult[TenantPackageRespVO] = page_result.convert(TenantPackageRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @tenant_package_controller.get("/simple-list", summary="获取租户套餐精简信息列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_tenant_package_list(
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
    ) -> Result[list[TenantPackageSimpleRespVO]]:
        package_list = await tenant_package_service.get_tenant_package_list_by_status(
            StatusEnum.ENABLE.code
        )
        simple_list = [TenantPackageSimpleRespVO.model_validate(item) for item in package_list]
        return Result.success(data=simple_list)

    @staticmethod
    @tenant_package_controller.get("/export-fields", summary="获取租户套餐可导出字段列表")
    @RoutePolicy(
        permissions=("system:tenant:package:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_tenant_package_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(TenantPackageRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @tenant_package_controller.get(
        "/export-excel", summary="导出租户套餐", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:tenant:package:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_tenant_package_list(
        page_req_vo: TenantPackageExportReqVO = Query(),
        tenant_package_service: TenantPackageService = Depends(DiDependency(TenantPackageService)),
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
        list_data_page: PageResult[
            TenantPackageDO
        ] = await tenant_package_service.get_tenant_package_page(page_req_vo)
        list_data: list[TenantPackageDO] = list_data_page.items
        tenant_package_resp_list: list[TenantPackageRespVO] = [
            TenantPackageRespVO.model_validate(package) for package in list_data
        ]
        filename = "租户套餐数据"
        file_data = await excel_writer.write(
            "数据",
            TenantPackageRespVO,
            tenant_package_resp_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
