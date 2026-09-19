from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.page import PageResult, PageSettings
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
from module_system.controller.admin.sms.vo.log.log_export_req_vo import SmsLogExportReqVO
from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO
from module_system.controller.admin.sms.vo.log.log_resp_vo import SmsLogRespVO
from module_system.dal.dataobject.sms.sms_log_do import SmsLogDO
from module_system.service.sms.sms_log_service import SmsLogService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

sms_log_controller = APIRouter(prefix="/sms/log", tags=["System - 短信日志管理"])


class SmsLogController:
    @staticmethod
    @sms_log_controller.get("/page", summary="获得短信日志分页")
    @RoutePolicy(
        permissions=("system:sms:log:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_sms_log_page(
        page_req_vo: SmsLogPageReqVO = Query(),
        sms_log_service: SmsLogService = Depends(DiDependency(SmsLogService)),
    ) -> Result[PageResult[SmsLogRespVO]]:
        page_result: PageResult[SmsLogDO] = await sms_log_service.get_sms_log_page(page_req_vo)
        resp_vo: PageResult[SmsLogRespVO] = page_result.convert(SmsLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @sms_log_controller.get("/export-fields", summary="获取短信日志可导出字段列表")
    @RoutePolicy(
        permissions=("system:sms:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_sms_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(SmsLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @sms_log_controller.get(
        "/export-excel", summary="导出短信日志 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:sms:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_sms_log_excel(
        page_req_vo: SmsLogExportReqVO = Query(),
        sms_log_service: SmsLogService = Depends(DiDependency(SmsLogService)),
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
        page_result: PageResult[SmsLogDO] = await sms_log_service.get_sms_log_page(page_req_vo)
        excel_list: list[SmsLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, SmsLogRespVO
        )
        filename = "短信日志"
        file_data = await excel_writer.write(
            "数据", SmsLogRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
