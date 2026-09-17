from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.exception.exceptions.service_exception import ServiceException
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
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO
from module_infra.controller.admin.mq.vo.mq.mq_resp_vo import MqRespVO
from module_infra.controller.admin.mq.vo.mq.mq_save_req_vo import MqSaveReqVO
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.dal.dataobject.mq.mq_do import MqDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.mq.mq_definition_service import MqDefinitionService

mq_controller = APIRouter(prefix="/mq", tags=["Infra - MQ 消息定义管理"])


class MqController:
    @staticmethod
    @mq_controller.post("/create", summary="创建消息定义")
    @RoutePolicy(
        permissions=("infra:mq:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_mq_definition(
        create_req_vo: MqSaveReqVO,
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
    ) -> Result[SnowflakeIdStr]:
        definition_id = await mq_definition_service.create_mq_definition(create_req_vo)
        return Result.success(data=definition_id)

    @staticmethod
    @mq_controller.put("/update", summary="更新消息定义")
    @RoutePolicy(
        permissions=("infra:mq:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_mq_definition(
        update_req_vo: MqSaveReqVO,
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
    ) -> Result[bool]:
        await mq_definition_service.update_mq_definition(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @mq_controller.delete("/delete", summary="删除消息定义")
    @RoutePolicy(
        permissions=("infra:mq:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_mq_definition(
        req_vo: IdReqVO = Query(),
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
    ) -> Result[bool]:
        await mq_definition_service.delete_mq_definition(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @mq_controller.get("/get", summary="获得消息定义")
    @RoutePolicy(permissions=("infra:mq:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_mq_definition(
        req_vo: IdReqVO = Query(),
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
    ) -> Result[MqRespVO]:
        definition = await mq_definition_service.get_mq_definition(req_vo.id)
        if not definition:
            raise ServiceException(ErrorCodeConstants.MQ_DEFINITION_NOT_EXISTS)
        resp = MqRespVO.model_validate(definition)
        return Result.success(data=resp)

    @staticmethod
    @mq_controller.get("/page", summary="获得消息定义分页")
    @RoutePolicy(permissions=("infra:mq:query",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_mq_definition_page(
        request: Request,
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
    ) -> Result[PageResult[MqRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, MqPageReqVO)
        page_result: PageResult[MqDO] = await mq_definition_service.get_mq_definition_page(
            page_req_vo
        )
        resp_vo: PageResult[MqRespVO] = page_result.convert(MqRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @mq_controller.get("/export-fields", summary="获取消息定义可导出字段列表")
    @RoutePolicy(
        permissions=("infra:mq:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_mq_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(MqRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @mq_controller.get("/export-excel", summary="导出消息定义", response_class=StreamingResponse)
    @RoutePolicy(
        permissions=("infra:mq:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_mq_definition_list(
        request: Request,
        mq_definition_service: MqDefinitionService = Depends(DiDependency(MqDefinitionService)),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, MqPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[MqDO] = await mq_definition_service.get_mq_definition_page(
            page_req_vo
        )
        excel_list: list[MqRespVO] = ConversionUtils.list_to_vo_list(page_result.items, MqRespVO)
        filename = "消息定义数据"
        file_data = await excel_writer.write(
            "数据", MqRespVO, excel_list, providers=excel_providers, fields=fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
