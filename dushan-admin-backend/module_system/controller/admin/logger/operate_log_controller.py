from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

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
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_export_req_vo import (
    OperateLogExportReqVO,
)
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_page_req_vo import (
    OperateLogPageReqVO,
)
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_resp_vo import (
    OperateLogRespVO,
)
from module_system.dal.dataobject.logger.operate_log_do import OperateLogDO
from module_system.service.logger.operate_log_service import OperateLogService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

operate_log_controller = APIRouter(prefix="/logger/operate-log", tags=["System - 操作日志管理"])


class OperateLogController:
    @staticmethod
    @operate_log_controller.get("/page", summary="查看操作日志分页列表")
    @RoutePolicy(
        permissions=("system:logger:operate-log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def page_operate_log(
        page_req_vo: OperateLogPageReqVO = Query(),
        operate_log_service: OperateLogService = Depends(DiDependency(OperateLogService)),
    ) -> Result[PageResult[OperateLogRespVO]]:
        page_result: PageResult[OperateLogDO] = await operate_log_service.get_operate_log_page_vo(
            page_req_vo
        )
        resp_vo: PageResult[OperateLogRespVO] = page_result.convert(OperateLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @operate_log_controller.get("/export-fields", summary="获取操作日志可导出字段列表")
    @RoutePolicy(
        permissions=("system:logger:operate-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_operate_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(OperateLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @operate_log_controller.get(
        "/export-excel", summary="导出操作日志", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:logger:operate-log:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_operate_log(
        page_req_vo: OperateLogExportReqVO = Query(),
        operate_log_service: OperateLogService = Depends(DiDependency(OperateLogService)),
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
        page_result: PageResult[OperateLogDO] = await operate_log_service.get_operate_log_page_vo(
            page_req_vo
        )
        excel_list: list[OperateLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, OperateLogRespVO
        )
        filename = "操作日志"
        file_data = await excel_writer.write(
            "数据",
            OperateLogRespVO,
            excel_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
