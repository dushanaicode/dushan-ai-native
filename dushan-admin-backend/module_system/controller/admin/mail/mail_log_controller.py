from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.mail.vo.log.log_export_req_vo import MailLogExportReqVO
from module_system.controller.admin.mail.vo.log.log_page_req_vo import MailLogPageReqVO
from module_system.controller.admin.mail.vo.log.log_resp_vo import MailLogRespVO
from module_system.dal.dataobject.mail.mail_log_do import MailLogDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.mail.mail_log_service import MailLogService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

mail_log_controller = APIRouter(prefix="/mail/log", tags=["System - 邮箱日志管理"])


class MailLogController:
    @staticmethod
    @mail_log_controller.get("/page", summary="获得邮箱日志分页")
    @RoutePolicy(
        permissions=("system:mail:log:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_mail_log_page(
        page_req_vo: MailLogPageReqVO = Query(),
        mail_log_service: MailLogService = Depends(DiDependency(MailLogService)),
    ) -> Result[PageResult[MailLogRespVO]]:
        page_result: PageResult[MailLogDO] = await mail_log_service.get_mail_log_page(page_req_vo)
        resp_vo: PageResult[MailLogRespVO] = page_result.convert(MailLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @mail_log_controller.get("/get", summary="获得邮箱日志")
    @RoutePolicy(
        permissions=("system:mail:log:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_mail_log(
        req_vo: IdReqVO = Query(),
        mail_log_service: MailLogService = Depends(DiDependency(MailLogService)),
    ) -> Result[MailLogRespVO]:
        mail_log = await mail_log_service.get_mail_log(req_vo.id)
        data = MailLogRespVO.model_validate(mail_log) if mail_log else None
        return Result.success(data=data)

    @staticmethod
    @mail_log_controller.get("/export-fields", summary="获取邮箱日志可导出字段列表")
    @RoutePolicy(
        permissions=("system:mail:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_mail_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(MailLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @mail_log_controller.get(
        "/export-excel", summary="导出邮箱日志", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:mail:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_mail_log_list(
        page_req_vo: MailLogExportReqVO = Query(),
        mail_log_service: MailLogService = Depends(DiDependency(MailLogService)),
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
        page_result: PageResult[MailLogDO] = await mail_log_service.get_mail_log_page(page_req_vo)
        list_data = page_result.items
        resp_list: list[MailLogRespVO] = [MailLogRespVO.model_validate(item) for item in list_data]
        filename = "邮箱日志数据"
        file_data = await excel_writer.write(
            "数据", MailLogRespVO, resp_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
