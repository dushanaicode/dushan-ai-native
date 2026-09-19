from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
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
from module_infra.controller.admin.config.vo.type.type_module_req_vo import ConfigTypeModuleReqVO
from module_infra.controller.admin.config.vo.type.type_page_req_vo import ConfigTypePageReqVO
from module_infra.controller.admin.config.vo.type.type_resp_vo import ConfigTypeRespVO
from module_infra.controller.admin.config.vo.type.type_save_req_vo import ConfigTypeSaveReqVO
from module_infra.controller.admin.config.vo.type.type_simple_resp_vo import ConfigTypeSimpleRespVO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO
from module_infra.service.config.config_type_service import ConfigTypeService

config_type_controller = APIRouter(prefix="/config/type", tags=["Infra - 配置类型管理"])


class ConfigTypeController:
    @staticmethod
    @config_type_controller.post("/create", summary="创建配置类型")
    @RoutePolicy(
        permissions=("infra:config:type:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_config_type(
        create_req_vo: ConfigTypeSaveReqVO,
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[SnowflakeIdStr]:
        id = await config_type_service.create_config_type(create_req_vo)
        return Result.success(data=id)

    @staticmethod
    @config_type_controller.put("/update", summary="修改配置类型")
    @RoutePolicy(
        permissions=("infra:config:type:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_config_type(
        update_req_vo: ConfigTypeSaveReqVO,
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[bool]:
        await config_type_service.update_config_type(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @config_type_controller.put("/update-status", summary="修改配置类型状态")
    @RoutePolicy(
        permissions=("infra:config:type:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_config_type_status(
        req_vo: UpdateStatusReqVO,
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[bool]:
        await config_type_service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @config_type_controller.delete("/delete", summary="删除配置类型")
    @RoutePolicy(
        permissions=("infra:config:type:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_config_type(
        req_vo: IdReqVO = Query(),
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[bool]:
        await config_type_service.delete_config_type(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @config_type_controller.delete("/delete-list", summary="批量删除配置类型")
    @RoutePolicy(
        permissions=("infra:config:type:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_config_type_batch(
        req_vo: IdListReqVO = Query(),
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[int]:
        deleted_count = await config_type_service.delete_config_type_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @config_type_controller.get("/page", summary="获得配置类型分页列表")
    @RoutePolicy(
        permissions=("infra:config:type:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def page_config_types(
        request: Request,
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[PageResult[ConfigTypeRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ConfigTypePageReqVO)
        page_result: PageResult[InfraConfigTypeDO] = await config_type_service.get_config_type_page(
            page_req_vo
        )
        resp_vo: PageResult[ConfigTypeRespVO] = page_result.convert(ConfigTypeRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @config_type_controller.get("/get", summary="查询配置类型详细")
    @RoutePolicy(
        permissions=("infra:config:type:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_config_type(
        req_vo: IdReqVO = Query(),
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[ConfigTypeRespVO]:
        config_type = await config_type_service.get_config_type_by_id(req_vo.id)
        resp = ConfigTypeRespVO.model_validate(config_type)
        return Result.success(data=resp)

    @staticmethod
    @config_type_controller.get(
        "/list-all-simple", summary="获得全部配置类型列表", include_in_schema=True
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_config_type_list(
        req_vo: ConfigTypeModuleReqVO = Query(),
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
    ) -> Result[list]:
        if req_vo.module:
            list_do = await config_type_service.get_config_types_by_module(req_vo.module)
        else:
            list_do = await config_type_service.get_config_type_list()
        simple_list = [ConfigTypeSimpleRespVO.model_validate(item) for item in list_do]
        return Result.success(data=simple_list)

    @staticmethod
    @config_type_controller.get("/export-fields", summary="获取配置类型可导出字段列表")
    @RoutePolicy(
        permissions=("infra:config:type:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_config_type_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(ConfigTypeRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @config_type_controller.get(
        "/export-excel", summary="导出配置类型", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:config:type:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_config_type_excel(
        request: Request,
        config_type_service: ConfigTypeService = Depends(DiDependency(ConfigTypeService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, ConfigTypePageReqVO)
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[InfraConfigTypeDO] = await config_type_service.get_config_type_page(
            page_req_vo
        )
        excel_list: list[ConfigTypeRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, ConfigTypeRespVO
        )
        filename = "配置类型"
        file_data = await excel_writer.write(
            "数据",
            ConfigTypeRespVO,
            excel_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
