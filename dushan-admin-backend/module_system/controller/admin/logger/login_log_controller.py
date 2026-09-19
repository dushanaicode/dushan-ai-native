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
from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_export_req_vo import (
    LoginLogExportReqVO,
)
from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_page_req_vo import (
    LoginLogPageReqVO,
)
from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_resp_vo import (
    LoginLogRespVO,
)
from module_system.dal.dataobject.logger.login_log_do import LoginLogDO
from module_system.service.logger.login_log_service import LoginLogService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

login_log_controller = APIRouter(prefix="/logger/login-log", tags=["System - 登录日志管理"])


class LoginLogController:
    @staticmethod
    @login_log_controller.get("/page", summary="获得登录日志分页列表")
    @RoutePolicy(
        permissions=("system:logger:login-log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_login_log_page(
        page_req_vo: LoginLogPageReqVO = Query(),
        login_log_service: LoginLogService = Depends(DiDependency(LoginLogService)),
    ) -> Result[PageResult[LoginLogRespVO]]:
        page_result: PageResult[LoginLogDO] = await login_log_service.get_login_log_page(
            page_req_vo
        )
        resp_vo: PageResult[LoginLogRespVO] = page_result.convert(LoginLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @login_log_controller.get("/export-fields", summary="获取登录日志可导出字段列表")
    @RoutePolicy(
        permissions=("system:logger:login-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_login_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(LoginLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @login_log_controller.get(
        "/export-excel", summary="导出登录日志 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:logger:login-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_login_log(
        page_req_vo: LoginLogExportReqVO = Query(),
        login_log_service: LoginLogService = Depends(DiDependency(LoginLogService)),
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
        page_result: PageResult[LoginLogDO] = await login_log_service.get_login_log_page(
            page_req_vo
        )
        excel_list: list[LoginLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, LoginLogRespVO
        )
        filename = "登录日志"
        file_data = await excel_writer.write(
            "数据", LoginLogRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
