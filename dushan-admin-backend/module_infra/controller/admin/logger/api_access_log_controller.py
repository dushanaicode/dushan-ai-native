from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

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
    AccessLogPolicy,
    FileResult,
    OperateTypeEnum,
    RequestUtils,
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.logger.vo.apiaccesslog.apiaccesslog_api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)
from module_infra.controller.admin.logger.vo.apiaccesslog.apiaccesslog_api_access_log_resp_vo import (
    ApiAccessLogRespVO,
)
from module_infra.dal.dataobject.logger.api_access_log_do import ApiAccessLogDO
from module_infra.service.logger.api_access_log_service import ApiAccessLogService

api_access_log_controller = APIRouter(
    prefix="/logger/api-access-log", tags=["Infra - API 访问日志管理"]
)


class ApiAccessLogController:
    @staticmethod
    @api_access_log_controller.get("/page", summary="获得 API 访问日志分页")
    @AccessLogPolicy(
        enabled=True,
        operate_module="访问日志",
        operate_name="查询访问日志",
        operate_type=OperateTypeEnum.GET,
    )
    @RoutePolicy(
        permissions=("infra:logger:api-access-log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_api_access_log_page(
        request: Request,
        api_access_log_service: ApiAccessLogService = Depends(DiDependency(ApiAccessLogService)),
    ) -> Result[PageResult[ApiAccessLogRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ApiAccessLogPageReqVO)
        page_result: PageResult[
            ApiAccessLogDO
        ] = await api_access_log_service.get_api_access_log_page(page_req_vo)
        resp_vo: PageResult[ApiAccessLogRespVO] = page_result.convert(ApiAccessLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @api_access_log_controller.get("/export-fields", summary="获取 API 访问日志可导出字段列表")
    @RoutePolicy(
        permissions=("infra:logger:api-access-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_api_access_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(ApiAccessLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @api_access_log_controller.get(
        "/export-excel", summary="导出 API 访问日志 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:logger:api-access-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_api_access_log_excel(
        request: Request,
        api_access_log_service: ApiAccessLogService = Depends(DiDependency(ApiAccessLogService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ApiAccessLogPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[
            ApiAccessLogDO
        ] = await api_access_log_service.get_api_access_log_page(page_req_vo)
        excel_list: list[ApiAccessLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, ApiAccessLogRespVO
        )
        filename = "API访问日志"
        file_data = await excel_writer.write(
            "数据", ApiAccessLogRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
