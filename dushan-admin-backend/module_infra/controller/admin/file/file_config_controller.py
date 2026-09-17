from fastapi import APIRouter, Depends, Query, Request

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.file.vo.config.file_config_page_req_vo import FileConfigPageReqVO
from module_infra.controller.admin.file.vo.config.file_config_resp_vo import FileConfigRespVO
from module_infra.controller.admin.file.vo.config.file_config_save_req_vo import FileConfigSaveReqVO
from module_infra.controller.admin.file.vo.config.file_config_simple_resp_vo import (
    FileConfigSimpleRespVO,
)
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.service.file.file_config_service import FileConfigService

file_config_controller = APIRouter(prefix="/file/config", tags=["Infra - 文件配置管理"])


class FileConfigController:
    @staticmethod
    @file_config_controller.post("/create", summary="创建文件配置")
    @RoutePolicy(
        permissions=("infra:file:config:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_file_config(
        create_req_vo: FileConfigSaveReqVO,
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[SnowflakeIdStr]:
        config_id = await file_config_service.create_file_config(create_req_vo)
        return Result.success(data=config_id)

    @staticmethod
    @file_config_controller.put("/update", summary="更新文件配置")
    @RoutePolicy(
        permissions=("infra:file:config:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_file_config(
        update_req_vo: FileConfigSaveReqVO,
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[bool]:
        await file_config_service.update_file_config(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @file_config_controller.put("/update-master", summary="更新文件配置为 Master")
    @RoutePolicy(
        permissions=("infra:file:config:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_file_config_master(
        req_vo: IdReqVO = Query(),
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[bool]:
        await file_config_service.update_file_config_master(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @file_config_controller.delete("/delete", summary="删除文件配置")
    @RoutePolicy(
        permissions=("infra:file:config:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_file_config(
        req_vo: IdReqVO = Query(),
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[bool]:
        await file_config_service.delete_file_config(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @file_config_controller.delete("/delete-list", summary="批量删除文件配置")
    @RoutePolicy(
        permissions=("infra:file:config:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_file_config_batch(
        req_vo: IdListReqVO = Query(),
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[int]:
        deleted_count = await file_config_service.delete_file_config_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @file_config_controller.get("/get", summary="获得文件配置")
    @RoutePolicy(
        permissions=("infra:file:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_file_config(
        req_vo: IdReqVO = Query(),
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[FileConfigRespVO]:
        config = await file_config_service.get_file_config(req_vo.id)
        config_resp = None if config is None else FileConfigRespVO.model_validate(config)
        return Result.success(data=config_resp)

    @staticmethod
    @file_config_controller.get("/page", summary="获得文件配置分页")
    @RoutePolicy(
        permissions=("infra:file:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_file_config_page(
        request: Request,
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[PageResult[FileConfigRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, FileConfigPageReqVO)
        page_result: PageResult[FileConfigDO] = await file_config_service.get_file_config_page(
            page_req_vo
        )
        resp_vo: PageResult[FileConfigRespVO] = page_result.convert(FileConfigRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @file_config_controller.get("/simple-list", summary="获取文件配置精简列表")
    @RoutePolicy(
        permissions=("infra:file:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_file_config_simple_list(
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[list[FileConfigSimpleRespVO]]:
        config_list = await file_config_service.get_file_config_list()
        response = [FileConfigSimpleRespVO.model_validate(cfg) for cfg in config_list]
        return Result.success(data=response)

    @staticmethod
    @file_config_controller.get("/test", summary="测试文件配置是否正确")
    @RoutePolicy(
        permissions=("infra:file:config:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def test_file_config(
        req_vo: IdReqVO = Query(),
        file_config_service: FileConfigService = Depends(DiDependency(FileConfigService)),
    ) -> Result[str]:
        url = await file_config_service.test_file_config(req_vo.id)
        return Result.success(data=url)
