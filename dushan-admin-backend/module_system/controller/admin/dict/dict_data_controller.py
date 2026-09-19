from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import StatusEnum
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
    AccessLogPolicy,
    FileResult,
    Result,
    RoutePolicy,
)
from module_system.controller.admin.dict.vo.data.data_export_req_vo import DictDataExportReqVO
from module_system.controller.admin.dict.vo.data.data_page_req_vo import DictDataPageReqVO
from module_system.controller.admin.dict.vo.data.data_resp_vo import DictDataRespVO
from module_system.controller.admin.dict.vo.data.data_save_req_vo import DictDataSaveReqVO
from module_system.controller.admin.dict.vo.data.data_simple_resp_vo import DictDataSimpleRespVO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO
from module_system.service.dict.dict_data_service import DictDataService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

dict_data_controller = APIRouter(prefix="/dict/data", tags=["System - 字典数据管理"])


class DictDataController:
    @staticmethod
    @dict_data_controller.post("/create", summary="新增字典数据")
    @RoutePolicy(
        permissions=("system:dict:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_dict_data(
        create_req_vo: DictDataSaveReqVO,
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[SnowflakeIdStr]:
        id = await dict_data_service.create_dict_data(create_req_vo)
        return Result.success(data=id)

    @staticmethod
    @dict_data_controller.put("/update", summary="修改字典数据")
    @RoutePolicy(
        permissions=("system:dict:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_dict_data(
        update_req_vo: DictDataSaveReqVO,
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[bool]:
        await dict_data_service.update_dict_data(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @dict_data_controller.put("/update-status", summary="修改字典数据状态")
    @RoutePolicy(
        permissions=("system:dict:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_status(
        req_vo: UpdateStatusReqVO, service: DictDataService = Depends(DiDependency(DictDataService))
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @dict_data_controller.delete("/delete", summary="删除字典数据")
    @RoutePolicy(
        permissions=("system:dict:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dict_data(
        req_vo: IdReqVO = Query(),
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[bool]:
        await dict_data_service.delete_dict_data(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @dict_data_controller.delete("/delete-list", summary="批量删除字典数据")
    @RoutePolicy(
        permissions=("system:dict:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dict_data_batch(
        req_vo: IdListReqVO = Query(),
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[int]:
        deleted_count = await dict_data_service.delete_dict_data_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @dict_data_controller.get(
        "/simple-list", summary="获得全部字典数据列表", include_in_schema=True
    )
    @AccessLogPolicy(enabled=False)
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_dict_data_list(
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[list]:
        list_data = await dict_data_service.get_dict_data_list(StatusEnum.ENABLE.code, None)
        simple_list = [DictDataSimpleRespVO.model_validate(item) for item in list_data]
        return Result.success(data=simple_list)

    @staticmethod
    @dict_data_controller.get("/page", summary="获得字典数据的分页列表")
    @RoutePolicy(
        permissions=("system:dict:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_dict_data_page(
        page_req_vo: DictDataPageReqVO = Query(),
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[PageResult[DictDataRespVO]]:
        page_result: PageResult[DictDataDO] = await dict_data_service.get_dict_data_page(
            page_req_vo
        )
        resp_vo: PageResult[DictDataRespVO] = page_result.convert(DictDataRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @dict_data_controller.get("/get", summary="查询字典数据详细")
    @RoutePolicy(
        permissions=("system:dict:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_dict_data(
        req_vo: IdReqVO = Query(),
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
    ) -> Result[DictDataRespVO]:
        dict_data = await dict_data_service.get_dict_data(req_vo.id)
        return Result.success(data=DictDataRespVO.model_validate(dict_data))

    @staticmethod
    @dict_data_controller.get("/export-fields", summary="获取字典数据可导出字段列表")
    @RoutePolicy(
        permissions=("system:dict:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_user_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(DictDataRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @dict_data_controller.get(
        "/export-excel", summary="导出字典数据", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:dict:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_dict_data(
        page_req_vo: DictDataExportReqVO = Query(),
        dict_data_service: DictDataService = Depends(DiDependency(DictDataService)),
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
        page_result: PageResult[DictDataDO] = await dict_data_service.get_dict_data_page(
            page_req_vo
        )
        excel_list: list[DictDataRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, DictDataRespVO
        )
        filename = "字典数据"
        file_data = await excel_writer.write(
            "数据", DictDataRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
