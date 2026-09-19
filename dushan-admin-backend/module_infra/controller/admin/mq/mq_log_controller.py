from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.exception import ServiceException
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdReqVO
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
    RequestUtils,
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.mq.vo.log.log_page_req_vo import MqLogPageReqVO
from module_infra.controller.admin.mq.vo.log.log_resp_vo import MqLogRespVO
from module_infra.dal.dataobject.mq.mq_log_do import MqLogDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.mq.mq_log_service import MqLogService

mq_log_controller = APIRouter(prefix="/mq/log", tags=["Infra - MQ 消费日志管理"])


class MqLogController:
    @staticmethod
    @mq_log_controller.get("/get", summary="获得消费日志")
    @RoutePolicy(
        permissions=("infra:mq:log:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_log(
        req_vo: IdReqVO = Query(),
        mq_log_service: MqLogService = Depends(DiDependency(MqLogService)),
    ) -> Result[MqLogRespVO]:
        log = await mq_log_service.get_log(req_vo.id)
        if not log:
            raise ServiceException(ErrorCodeConstants.MQ_MESSAGE_NOT_EXISTS, "消费日志不存在")
        resp = MqLogRespVO.model_validate(log)
        return Result.success(data=resp)

    @staticmethod
    @mq_log_controller.get("/page", summary="获得消费日志分页")
    @RoutePolicy(
        permissions=("infra:mq:log:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_log_page(
        request: Request, mq_log_service: MqLogService = Depends(DiDependency(MqLogService))
    ) -> Result[PageResult[MqLogRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, MqLogPageReqVO)
        page_result: PageResult[MqLogDO] = await mq_log_service.get_log_page(page_req_vo)
        resp_vo: PageResult[MqLogRespVO] = page_result.convert(MqLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @mq_log_controller.get("/export-fields", summary="获取MQ日志可导出字段列表")
    @RoutePolicy(
        permissions=("infra:mq:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_mq_log_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(MqLogRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @mq_log_controller.get("/export-excel", summary="导出MQ日志", response_class=StreamingResponse)
    @RoutePolicy(
        permissions=("infra:mq:log:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_mq_log_list(
        request: Request,
        mq_log_service: MqLogService = Depends(DiDependency(MqLogService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, MqLogPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[MqLogDO] = await mq_log_service.get_log_page(page_req_vo)
        excel_list: list[MqLogRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, MqLogRespVO
        )
        filename = "MQ日志数据"
        file_data = await excel_writer.write(
            "数据", MqLogRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
