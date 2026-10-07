from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

from framework.common.page import PageResult
from framework.common.utils import ConversionUtils
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_excel.public import (
    ExcelWriter,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityRealm,
)
from framework.starter_web.public import (
    FileResult,
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_export_req_vo import (
    ApiErrorLogExportReqVO,
)
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_resp_vo import (
    ApiErrorLogRespVO,
)
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_update_status_req_vo import (
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
        page_req_vo: ApiErrorLogPageReqVO = Query(),
        api_error_log_service: ApiErrorLogService = Depends(DiDependency(ApiErrorLogService)),
    ) -> Result[PageResult[ApiErrorLogRespVO]]:
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
        page_req_vo: ApiErrorLogExportReqVO = Query(),
        api_error_log_service: ApiErrorLogService = Depends(DiDependency(ApiErrorLogService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> StreamingResponse:
        excel_writer.prepare_export_query(page_req_vo)
        page_result: PageResult[ApiErrorLogDO] = await api_error_log_service.get_api_error_log_page(
            page_req_vo
        )
        excel_list: list[ApiErrorLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, ApiErrorLogRespVO
        )
        filename = "API错误日志"
        file_data = await excel_writer.write(
            "数据",
            ApiErrorLogRespVO,
            excel_list,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
