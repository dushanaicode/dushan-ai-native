from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.common.utils import ConversionUtils
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
from module_system.controller.admin.dict.vo.type.type_export_req_vo import DictTypeExportReqVO
from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO
from module_system.controller.admin.dict.vo.type.type_resp_vo import DictTypeRespVO
from module_system.controller.admin.dict.vo.type.type_save_req_vo import DictTypeSaveReqVO
from module_system.controller.admin.dict.vo.type.type_simple_resp_vo import DictTypeSimpleRespVO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO
from module_system.service.dict.dict_type_service import DictTypeService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

dict_type_controller = APIRouter(prefix="/dict/type", tags=["System - 字典类型管理"])


class DictTypeController:
    @staticmethod
    @dict_type_controller.post("/create", summary="创建字典类型")
    @RoutePolicy(
        permissions=("system:dict:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_dict_type(
        create_req_vo: DictTypeSaveReqVO,
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[SnowflakeIdStr]:
        id = await dict_type_service.create_dict_type(create_req_vo)
        return Result.success(data=id)

    @staticmethod
    @dict_type_controller.put("/update", summary="修改字典类型")
    @RoutePolicy(
        permissions=("system:dict:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_dict_type(
        update_req_vo: DictTypeSaveReqVO,
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[bool]:
        await dict_type_service.update_dict_type(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @dict_type_controller.put("/update-status", summary="修改字典类型状态")
    @RoutePolicy(
        permissions=("system:dict:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_status(
        req_vo: UpdateStatusReqVO, service: DictTypeService = Depends(DiDependency(DictTypeService))
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @dict_type_controller.delete("/delete", summary="删除字典类型")
    @RoutePolicy(
        permissions=("system:dict:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dict_type(
        req_vo: IdReqVO = Query(),
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[bool]:
        await dict_type_service.delete_dict_type(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @dict_type_controller.delete("/delete-list", summary="批量删除字典类型")
    @RoutePolicy(
        permissions=("system:dict:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dict_type_batch(
        req_vo: IdListReqVO = Query(),
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[int]:
        deleted_count = await dict_type_service.delete_dict_type_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @dict_type_controller.get("/page", summary="获得字典类型分页列表")
    @RoutePolicy(
        permissions=("system:dict:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def page_dict_types(
        page_req_vo: DictTypePageReqVO = Query(),
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[PageResult[DictTypeRespVO]]:
        page_result: PageResult[DictTypeDO] = await dict_type_service.get_dict_type_page(
            page_req_vo
        )
        resp_vo: PageResult[DictTypeRespVO] = page_result.convert(DictTypeRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @dict_type_controller.get("/get", summary="查询字典类型详细")
    @RoutePolicy(
        permissions=("system:dict:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_dict_type(
        req_vo: IdReqVO = Query(),
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[DictTypeRespVO]:
        dict_type = await dict_type_service.get_dict_type_by_id(req_vo.id)
        resp = DictTypeRespVO.model_validate(dict_type)
        return Result.success(data=resp)

    @staticmethod
    @dict_type_controller.get("/simple-list", summary="获得全部字典类型列表")
    @dict_type_controller.get(
        "/list-all-simple", summary="获得全部字典类型列表", include_in_schema=True
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_dict_type_list(
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
    ) -> Result[list]:
        list_do = await dict_type_service.get_dict_type_list()
        simple_list = [DictTypeSimpleRespVO.model_validate(item) for item in list_do]
        return Result.success(data=simple_list)

    @staticmethod
    @dict_type_controller.get("/export-fields", summary="获取字典类型可导出字段列表")
    @RoutePolicy(
        permissions=("system:dict:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_user_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(DictTypeRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @dict_type_controller.get(
        "/export-excel", summary="导出数据类型", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:dict:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_dict_type_excel(
        page_req_vo: DictTypeExportReqVO = Query(),
        dict_type_service: DictTypeService = Depends(DiDependency(DictTypeService)),
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
        page_result: PageResult[DictTypeDO] = await dict_type_service.get_dict_type_page(
            page_req_vo
        )
        excel_list: list[DictTypeRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, DictTypeRespVO
        )
        filename = "字典类型"
        file_data = await excel_writer.write(
            "数据", DictTypeRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
