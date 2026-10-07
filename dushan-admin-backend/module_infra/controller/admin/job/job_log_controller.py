from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.common.schemas.request import IdReqVO
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
    FileResult,
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.job.vo.log.job_log_export_req_vo import JobLogExportReqVO
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO
from module_infra.controller.admin.job.vo.log.job_log_resp_vo import JobLogRespVO
from module_infra.dal.dataobject.job.job_log_do import JobLogDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
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
        if job_log is None:
            raise ServiceException(ErrorCodeConstants.JOB_LOG_NOT_EXISTS)
        job_log_resp = JobLogRespVO.model_validate(job_log)
        return Result.success(data=job_log_resp)

    @staticmethod
    @job_log_controller.get("/page", summary="获得定时任务日志分页")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job_log_page(
        page_req_vo: JobLogPageReqVO = Query(),
        job_log_service: JobLogService = Depends(DiDependency(JobLogService)),
    ) -> Result[PageResult[JobLogRespVO]]:
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
        page_req_vo: JobLogExportReqVO = Query(),
        job_log_service: JobLogService = Depends(DiDependency(JobLogService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> StreamingResponse:
        excel_writer.prepare_export_query(page_req_vo)
        page_result: PageResult[JobLogDO] = await job_log_service.get_job_log_page(page_req_vo)
        excel_list: list[JobLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, JobLogRespVO
        )
        filename = "任务日志"
        file_data = await excel_writer.write(
            "数据", JobLogRespVO, excel_list, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
