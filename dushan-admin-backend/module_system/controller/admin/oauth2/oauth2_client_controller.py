from fastapi import APIRouter, Depends, Query

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.oauth2.vo.client.oauth2_client_page_req_vo import (
    OAuth2ClientPageReqVO,
)
from module_system.controller.admin.oauth2.vo.client.oauth2_client_resp_vo import OAuth2ClientRespVO
from module_system.controller.admin.oauth2.vo.client.oauth2_client_save_req_vo import (
    OAuth2ClientSaveReqVO,
)
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.definitions.vo.update_status_req_vo import UpdateStatusReqVO
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService

oauth2_client_controller = APIRouter(prefix="/oauth2/client", tags=["System - OAuth2 客户端管理"])


class Oauth2ClientController:
    @staticmethod
    @oauth2_client_controller.post("/create", summary="创建 OAuth2 客户端")
    @RoutePolicy(
        permissions=("system:oauth2:client:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_oauth2_client(
        create_req_vo: OAuth2ClientSaveReqVO,
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[SnowflakeIdStr]:
        client_id = await oauth2_client_service.create_oauth2_client(create_req_vo)
        return Result.success(data=client_id)

    @staticmethod
    @oauth2_client_controller.put("/update", summary="更新 OAuth2 客户端")
    @RoutePolicy(
        permissions=("system:oauth2:client:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_oauth2_client(
        update_req_vo: OAuth2ClientSaveReqVO,
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[bool]:
        await oauth2_client_service.update_oauth2_client(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @oauth2_client_controller.put("/update-status", summary="修改OAuth2客户端状态")
    @RoutePolicy(
        permissions=("system:oauth2:client:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @oauth2_client_controller.delete("/delete", summary="删除 OAuth2 客户端")
    @RoutePolicy(
        permissions=("system:oauth2:client:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_oauth2_client(
        req_vo: IdReqVO = Query(),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[bool]:
        await oauth2_client_service.delete_oauth2_client(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @oauth2_client_controller.delete("/delete-list", summary="批量删除 OAuth2 客户端")
    @RoutePolicy(
        permissions=("system:oauth2:client:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_oauth2_client_batch(
        req_vo: IdListReqVO = Query(),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[int]:
        deleted_count = await oauth2_client_service.delete_oauth2_client_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @oauth2_client_controller.get("/get", summary="获得 OAuth2 客户端")
    @RoutePolicy(
        permissions=("system:oauth2:client:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_oauth2_client(
        req_vo: IdReqVO = Query(),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[OAuth2ClientRespVO]:
        client = await oauth2_client_service.get_oauth2_client(req_vo.id)
        client_resp = OAuth2ClientRespVO.model_validate(client)
        return Result.success(data=client_resp)

    @staticmethod
    @oauth2_client_controller.get("/page", summary="获得 OAuth2 客户端分页")
    @RoutePolicy(
        permissions=("system:oauth2:client:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_oauth2_client_page(
        page_req_vo: OAuth2ClientPageReqVO = Query(),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
    ) -> Result[PageResult[OAuth2ClientRespVO]]:
        page_result: PageResult[
            OAuth2ClientDO
        ] = await oauth2_client_service.get_oauth2_client_page(page_req_vo)
        resp_vo: PageResult[OAuth2ClientRespVO] = page_result.convert(OAuth2ClientRespVO)
        return Result.success(data=resp_vo)
