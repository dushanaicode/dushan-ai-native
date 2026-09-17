from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.datetime.core.date_utils import DateUtils
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_job.cron.cron_schedule import CronSchedule
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.job.vo.job.job_next_times_req_vo import JobNextTimesReqVO
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.controller.admin.job.vo.job.job_resp_vo import JobRespVO
from module_infra.controller.admin.job.vo.job.job_save_req_vo import JobSaveReqVO
from module_infra.controller.admin.job.vo.job.job_update_status_req_vo import JobUpdateStatusReqVO
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.dal.dataobject.job.job_do import JobDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.job.job_service import JobService

job_controller = APIRouter(prefix="/job", tags=["Infra - 定时任务管理"])


class JobController:
    @staticmethod
    @job_controller.post("/create", summary="创建定时任务")
    @RoutePolicy(
        permissions=("infra:job:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_job(
        create_req_vo: JobSaveReqVO, job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[SnowflakeIdStr]:
        job_id = await job_service.create_job(create_req_vo)
        return Result.success(data=job_id)

    @staticmethod
    @job_controller.put("/update", summary="更新定时任务")
    @RoutePolicy(
        permissions=("infra:job:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_job(
        update_req_vo: JobSaveReqVO, job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[bool]:
        await job_service.update_job(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @job_controller.put("/update-status", summary="更新定时任务的状态")
    @RoutePolicy(
        permissions=("infra:job:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_job_status(
        update_req_vo: JobUpdateStatusReqVO = Query(),
        job_service: JobService = Depends(DiDependency(JobService)),
    ) -> Result[bool]:
        await job_service.update_job_status(update_req_vo.id, update_req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @job_controller.delete("/delete", summary="删除定时任务")
    @RoutePolicy(
        permissions=("infra:job:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_job(
        req_vo: IdReqVO = Query(), job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[bool]:
        await job_service.delete_job(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @job_controller.delete("/delete-list", summary="批量删除定时任务")
    @RoutePolicy(
        permissions=("infra:job:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_job_batch(
        req_vo: IdListReqVO = Query(), job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[int]:
        deleted_count = await job_service.delete_job_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @job_controller.put("/trigger", summary="触发定时任务")
    @RoutePolicy(
        permissions=("infra:job:trigger",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def trigger_job(
        req_vo: IdReqVO = Query(), job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[bool]:
        await job_service.trigger_job(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @job_controller.post("/sync", summary="同步定时任务")
    @RoutePolicy(
        permissions=("infra:job:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def sync_job(job_service: JobService = Depends(DiDependency(JobService))) -> Result[bool]:
        await job_service.sync_job()
        return Result.success(data=True)

    @staticmethod
    @job_controller.get("/get", summary="获得定时任务")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job(
        req_vo: IdReqVO = Query(), job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[JobRespVO]:
        job = await job_service.get_job(req_vo.id)
        if not job:
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        job_resp = JobRespVO.model_validate(job)
        return Result.success(data=job_resp)

    @staticmethod
    @job_controller.get("/page", summary="获得定时任务分页")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job_page(
        request: Request, job_service: JobService = Depends(DiDependency(JobService))
    ) -> Result[PageResult[JobRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, JobPageReqVO)
        page_result: PageResult[JobDO] = await job_service.get_job_page(page_req_vo)
        resp_vo: PageResult[JobRespVO] = page_result.convert(JobRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @job_controller.get("/export-fields", summary="获取定时任务可导出字段列表")
    @RoutePolicy(
        permissions=("infra:job:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_job_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(JobRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @job_controller.get(
        "/export-excel", summary="导出定时任务 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:job:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_job_excel(
        request: Request,
        job_service: JobService = Depends(DiDependency(JobService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, JobPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[JobDO] = await job_service.get_job_page(page_req_vo)
        excel_list: list[JobRespVO] = [JobRespVO.model_validate(row) for row in page_result.items]
        filename = "定时任务"
        file_data = await excel_writer.write(
            "数据", JobRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @job_controller.get("/get_next_times", summary="获得定时任务的下 n 次执行时间")
    @RoutePolicy(permissions=("infra:job:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_job_next_times(
        req_vo: JobNextTimesReqVO = Query(),
        job_service: JobService = Depends(DiDependency(JobService)),
        date_utils: DateUtils = Depends(DiDependency(DateUtils)),
        job_settings: JobSettings = Depends(DiDependency(JobSettings)),
    ) -> Result[list[str]]:
        job = await job_service.get_job(req_vo.id)
        if job is None:
            raise ServiceException(ErrorCodeConstants.JOB_NOT_EXISTS)
        schedule = CronSchedule(
            job.cron_expression, job_settings.timezone or date_utils.get_timezone_name()
        )
        return Result.success(
            [
                value.isoformat()
                for value in schedule.preview(datetime.now(timezone.utc), req_vo.count)
            ]
        )
