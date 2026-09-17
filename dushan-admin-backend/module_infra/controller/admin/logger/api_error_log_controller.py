from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.collection.conversion_utils import ConversionUtils
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_resp_vo import (
    ApiErrorLogRespVO,
)
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_update_status_req_vo import (
    ApiErrorLogUpdateStatusReqVO,
)
from module_infra.dal.dataobject.logger.api_error_log_do import ApiErrorLogDO
from module_infra.service.logger.api_error_log_service import ApiErrorLogService

api_error_log_controller = APIRouter(
    prefix="/logger/api-error-log", tags=["Infra - API 错误日志管理"]
)


class ApiErrorLogController:
    @staticmethod
    @api_error_log_controller.put("/update-status", summary="更新 API 错误日志的状态")
    @RoutePolicy(
        permissions=("infra:logger:api-error-log:update-status",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_api_error_log_status(
        update_req_vo: ApiErrorLogUpdateStatusReqVO = Query(),
        api_error_log_service: ApiErrorLogService = Depends(DiDependency(ApiErrorLogService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        current_user_id: int | None = int(security.require().account_id)
        await api_error_log_service.update_api_error_log_process(
            log_id=update_req_vo.id,
            process_status=update_req_vo.process_status,
            process_user_id=current_user_id,
        )
        return Result.success(data=True)

    @staticmethod
    @api_error_log_controller.get("/page", summary="获得 API 错误日志分页")
    @RoutePolicy(
        permissions=("infra:logger:api-error-log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_api_error_log_page(
        request: Request,
        api_error_log_service: ApiErrorLogService = Depends(DiDependency(ApiErrorLogService)),
    ) -> Result[PageResult[ApiErrorLogRespVO]]:
        page_req_vo: ApiErrorLogPageReqVO = RequestUtils.validate_with_auto_list_params(
            request, ApiErrorLogPageReqVO
        )
        page_result: PageResult[ApiErrorLogDO] = await api_error_log_service.get_api_error_log_page(
            page_req_vo
        )
        resp_vo: PageResult[ApiErrorLogRespVO] = page_result.convert(ApiErrorLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @api_error_log_controller.get("/export-fields", summary="获取 API 错误日志可导出字段列表")
    @RoutePolicy(
        permissions=("infra:logger:api-error-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_api_error_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(ApiErrorLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @api_error_log_controller.get(
        "/export-excel", summary="导出 API 错误日志 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:logger:api-error-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_api_error_log_excel(
        request: Request,
        api_error_log_service: ApiErrorLogService = Depends(DiDependency(ApiErrorLogService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo: ApiErrorLogPageReqVO = RequestUtils.validate_with_auto_list_params(
            request, ApiErrorLogPageReqVO
        )
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[ApiErrorLogDO] = await api_error_log_service.get_api_error_log_page(
            page_req_vo
        )
        excel_list: list[ApiErrorLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, ApiErrorLogRespVO
        )
        filename = "API错误日志"
        file_data = await excel_writer.write(
            "数据", ApiErrorLogRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
