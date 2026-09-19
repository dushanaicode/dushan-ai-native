from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdReqVO, UpdateStatusReqVO
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
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_resp_vo import (
    DataSourceConfigRespVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_save_req_vo import (
    DataSourceConfigSaveReqVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_simple_resp_vo import (
    DataSourceConfigSimpleRespVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_status_req_vo import (
    DataSourceConfigStatusReqVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_test_resp_vo import (
    DataSourceConfigTestRespVO,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO
from module_infra.service.data_source.data_source_config_service import DataSourceConfigService

data_source_config_controller = APIRouter(prefix="/data-source", tags=["Infra - 数据源配置管理"])


class DataSourceConfigController:
    @staticmethod
    @data_source_config_controller.post("/create", summary="创建数据源配置")
    @RoutePolicy(
        permissions=("infra:data-source:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_data_source_config(
        create_req_vo: DataSourceConfigSaveReqVO,
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[SnowflakeIdStr]:
        config_id = await data_source_config_service.create_data_source_config(create_req_vo)
        return Result.success(data=config_id)

    @staticmethod
    @data_source_config_controller.put("/update", summary="更新数据源配置")
    @RoutePolicy(
        permissions=("infra:data-source:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_data_source_config(
        update_req_vo: DataSourceConfigSaveReqVO,
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[bool]:
        await data_source_config_service.update_data_source_config(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @data_source_config_controller.put("/update-status", summary="修改数据源配置状态")
    @RoutePolicy(
        permissions=("infra:data-source:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_data_source_config_status(
        req_vo: UpdateStatusReqVO,
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[bool]:
        await data_source_config_service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @data_source_config_controller.delete("/delete", summary="删除数据源配置")
    @RoutePolicy(
        permissions=("infra:data-source:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_data_source_config(
        req_vo: IdReqVO = Query(),
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[bool]:
        await data_source_config_service.delete_data_source_config(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @data_source_config_controller.get("/get", summary="获得数据源配置")
    @RoutePolicy(
        permissions=("infra:data-source:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_data_source_config(
        req_vo: IdReqVO = Query(),
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[DataSourceConfigRespVO]:
        data_source_config = await data_source_config_service.get_data_source_config(req_vo.id)
        if not data_source_config:
            return Result.success(data=None)
        config_resp = DataSourceConfigRespVO.model_validate(data_source_config)
        return Result.success(data=config_resp)

    @staticmethod
    @data_source_config_controller.get("/list", summary="获得数据源配置列表")
    @RoutePolicy(
        permissions=("infra:data-source:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_data_source_config_list(
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[list[DataSourceConfigRespVO]]:
        data_source_configs = await data_source_config_service.get_data_source_config_list()
        resp_list = [DataSourceConfigRespVO.model_validate(item) for item in data_source_configs]
        return Result.success(data=resp_list)

    @staticmethod
    @data_source_config_controller.get("/page", summary="获得数据源配置分页")
    @RoutePolicy(
        permissions=("infra:data-source:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_data_source_config_page(
        request: Request,
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[PageResult[DataSourceConfigRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(
            request, DataSourceConfigPageReqVO
        )
        page_result: PageResult[
            DataSourceConfigDO
        ] = await data_source_config_service.get_data_source_config_page(page_req_vo)
        resp_vo: PageResult[DataSourceConfigRespVO] = page_result.convert(DataSourceConfigRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @data_source_config_controller.get("/list-by-status", summary="根据状态获得数据源配置列表")
    @RoutePolicy(
        permissions=("infra:data-source:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_data_source_config_list_by_status(
        req_vo: DataSourceConfigStatusReqVO = Query(),
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[list[DataSourceConfigSimpleRespVO]]:
        data_source_configs = (
            await data_source_config_service.get_data_source_config_list_by_status(req_vo.status)
        )
        simple_resp_list = [
            DataSourceConfigSimpleRespVO.model_validate(item) for item in data_source_configs
        ]
        return Result.success(data=simple_resp_list)

    @staticmethod
    @data_source_config_controller.post("/test", summary="测试数据源配置")
    @RoutePolicy(
        permissions=("infra:data-source:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def test_data_source_config(
        req_vo: IdReqVO = Query(),
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
    ) -> Result[DataSourceConfigTestRespVO]:
        result, msg = await data_source_config_service.test_data_source_config(req_vo.id)
        test_resp = DataSourceConfigTestRespVO(success=result, message=msg)
        return Result.success(data=test_resp)

    @staticmethod
    @data_source_config_controller.get("/export-fields", summary="获取数据源配置可导出字段列表")
    @RoutePolicy(
        permissions=("infra:data-source:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_data_source_config_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(DataSourceConfigRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @data_source_config_controller.get(
        "/export-excel", summary="导出数据源配置", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("infra:data-source:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_data_source_config_list(
        request: Request,
        data_source_config_service: DataSourceConfigService = Depends(
            DiDependency(DataSourceConfigService)
        ),
        fields: list[str] = Query(None, description="导出的字段列表"),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(dictionaries=dictionaries)
        page_req_vo = RequestUtils.validate_with_auto_list_params(
            request, DataSourceConfigPageReqVO
        )
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[
            DataSourceConfigDO
        ] = await data_source_config_service.get_data_source_config_page(page_req_vo)
        list_data: list[DataSourceConfigDO] = page_result.items
        data_source_config_resp_list: list[DataSourceConfigRespVO] = [
            DataSourceConfigRespVO.model_validate(item) for item in list_data
        ]
        filename = "数据源配置"
        file_data = await excel_writer.write(
            "数据",
            DataSourceConfigRespVO,
            data_source_config_resp_list,
            providers=excel_providers,
            fields=fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
