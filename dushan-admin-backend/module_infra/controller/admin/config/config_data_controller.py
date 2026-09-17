from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.config.vo.data.data_key_req_vo import ConfigDataKeyReqVO
from module_infra.controller.admin.config.vo.data.data_page_req_vo import ConfigDataPageReqVO
from module_infra.controller.admin.config.vo.data.data_resp_vo import ConfigDataRespVO
from module_infra.controller.admin.config.vo.data.data_save_req_vo import ConfigDataSaveReqVO
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.config.config_data_service import ConfigDataService

config_data_controller = APIRouter(prefix="/config", tags=["Infra - 参数配置管理"])


class ConfigDataController:
    @staticmethod
    @config_data_controller.post("/create", summary="创建参数配置")
    @RoutePolicy(
        permissions=("infra:config:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_config(
        create_req_vo: ConfigDataSaveReqVO,
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[SnowflakeIdStr]:
        config_id = await config_data_service.create_config(create_req_vo)
        return Result.success(data=config_id)

    @staticmethod
    @config_data_controller.put("/update", summary="修改参数配置")
    @RoutePolicy(
        permissions=("infra:config:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_config(
        update_req_vo: ConfigDataSaveReqVO,
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[bool]:
        await config_data_service.update_config(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @config_data_controller.delete("/delete", summary="删除参数配置")
    @RoutePolicy(
        permissions=("infra:config:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_config(
        req_vo: IdReqVO = Query(),
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[bool]:
        await config_data_service.delete_config(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @config_data_controller.delete("/delete-list", summary="批量删除参数配置")
    @RoutePolicy(
        permissions=("infra:config:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_config_batch(
        req_vo: IdListReqVO = Query(),
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[int]:
        deleted_count = await config_data_service.delete_config_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @config_data_controller.get("/get", summary="获得参数配置")
    @RoutePolicy(
        permissions=("infra:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_config(
        req_vo: IdReqVO = Query(),
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[ConfigDataRespVO]:
        config_resp = await config_data_service.get_config_with_type_name(req_vo.id)
        return Result.success(data=config_resp)

    @staticmethod
    @config_data_controller.get(
        "/get-value-by-key",
        summary="根据参数键名查询参数值",
        description="不可见的配置，不允许返回给前端",
    )
    @RoutePolicy(scopes=(), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_config_value_by_key(
        req_vo: ConfigDataKeyReqVO = Query(),
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[str | None]:
        config = await config_data_service.get_config_by_key(req_vo.key)
        if config is None:
            return Result.success(data=None)
        if not config.visible:
            raise ServiceException(ErrorCodeConstants.CONFIG_DATA_GET_VALUE_ERROR_IF_VISIBLE)
        return Result.success(data=config.value)

    @staticmethod
    @config_data_controller.get("/page", summary="获取参数配置分页")
    @RoutePolicy(
        permissions=("infra:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_config_page(
        request: Request,
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
    ) -> Result[PageResult[ConfigDataRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ConfigDataPageReqVO)
        page_result = await config_data_service.get_config_page_with_type_name(page_req_vo)
        return Result.success(data=page_result)

    @staticmethod
    @config_data_controller.get("/export-fields", summary="获取参数配置可导出字段列表")
    @RoutePolicy(
        permissions=("infra:config:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_config_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(ConfigDataRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @config_data_controller.get(
        "/export-excel", summary="导出参数配置", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:config:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_config(
        request: Request,
        config_data_service: ConfigDataService = Depends(DiDependency(ConfigDataService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ConfigDataPageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        excel_list = await config_data_service.get_config_list_with_type_name(page_req_vo)
        filename = "参数配置"
        file_data = await excel_writer.write(
            "数据",
            ConfigDataRespVO,
            excel_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
