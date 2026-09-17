from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.collection.conversion_utils import ConversionUtils
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.job.vo.log.log_page_req_vo import JobLogPageReqVO
from module_infra.controller.admin.job.vo.log.log_resp_vo import JobLogRespVO
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.service.job.job_log_service import JobLogService

job_log_controller = APIRouter(prefix="/job/log", tags=["Infra - 定时任务日志管理"])


class JobLogController:
    @staticmethod
    @job_log_controller.get("/get", summary="获得定时任务日志")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job_log(
        req_vo: IdReqVO = Query(),
        job_log_service: JobLogService = Depends(DiDependency(JobLogService)),
    ) -> Result[JobLogRespVO]:
        job_log = await job_log_service.get_job_log(req_vo.id)
        job_log_resp = JobLogRespVO.model_validate(job_log)
        return Result.success(data=job_log_resp)

    @staticmethod
    @job_log_controller.get("/page", summary="获得定时任务日志分页")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job_log_page(
        request: Request, job_log_service: JobLogService = Depends(DiDependency(JobLogService))
    ) -> Result[PageResult[JobLogRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, JobLogPageReqVO)
        page_result: PageResult[JobLogDO] = await job_log_service.get_job_log_page(page_req_vo)
        resp_vo: PageResult[JobLogRespVO] = page_result.convert(JobLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @job_log_controller.get("/export-fields", summary="获取定时任务日志可导出字段列表")
    @RoutePolicy(
        permissions=("infra:job:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_job_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(JobLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @job_log_controller.get(
        "/export-excel", summary="导出定时任务日志 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:job:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_job_log_excel(
        request: Request,
        job_log_service: JobLogService = Depends(DiDependency(JobLogService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, JobLogPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[JobLogDO] = await job_log_service.get_job_log_page(page_req_vo)
        excel_list: list[JobLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, JobLogRespVO
        )
        filename = "任务日志"
        file_data = await excel_writer.write(
            "数据", JobLogRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
