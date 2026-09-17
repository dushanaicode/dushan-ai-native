from fastapi import APIRouter, Depends, Query

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.api.social.dto.social_wxa_subscribe_message_send_req_dto import (
    SocialWxaSubscribeMessageSendReqDTO,
)
from module_system.api.social.social_client_api import SocialClientApi
from module_system.controller.admin.social.vo.client.social_client_page_req_vo import (
    SocialClientPageReqVO,
)
from module_system.controller.admin.social.vo.client.social_client_resp_vo import SocialClientRespVO
from module_system.controller.admin.social.vo.client.social_client_save_req_vo import (
    SocialClientSaveReqVO,
)
from module_system.controller.admin.social.vo.client.subscribe_message_send_req_vo import (
    SubscribeMessageSendReqVO,
)
from module_system.dal.dataobject.social.social_client_do import SocialClientDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.definitions.vo.update_status_req_vo import UpdateStatusReqVO
from module_system.service.social.social_client_service import SocialClientService

social_client_controller = APIRouter(prefix="/social/client", tags=["System - 社交客户端管理"])


class SocialClientController:
    @staticmethod
    @social_client_controller.post("/create", summary="创建社交客户端")
    @RoutePolicy(
        permissions=("system:social:client:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_social_client(
        create_req_vo: SocialClientSaveReqVO,
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[SnowflakeIdStr]:
        client_id = await social_client_service.create_social_client(create_req_vo)
        return Result.success(data=client_id)

    @staticmethod
    @social_client_controller.put("/update", summary="更新社交客户端")
    @RoutePolicy(
        permissions=("system:social:client:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_social_client(
        update_req_vo: SocialClientSaveReqVO,
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[bool]:
        await social_client_service.update_social_client(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @social_client_controller.put("/update-status", summary="修改社交客户端状态")
    @RoutePolicy(
        permissions=("system:social:client:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @social_client_controller.delete("/delete", summary="删除社交客户端")
    @RoutePolicy(
        permissions=("system:social:client:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_social_client(
        req_vo: IdReqVO = Query(),
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[bool]:
        await social_client_service.delete_social_client(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @social_client_controller.delete("/delete-list", summary="批量删除社交客户端")
    @RoutePolicy(
        permissions=("system:social:client:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_social_client_batch(
        req_vo: IdListReqVO = Query(),
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[int]:
        deleted_count = await social_client_service.delete_social_client_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @social_client_controller.get("/get", summary="获得社交客户端")
    @RoutePolicy(
        permissions=("system:social:client:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_social_client(
        req_vo: IdReqVO = Query(),
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[SocialClientRespVO]:
        client = await social_client_service.get_social_client(req_vo.id)
        if client is None:
            return Result.success(data=None)
        data = SocialClientRespVO.model_validate(client)
        return Result.success(data=data)

    @staticmethod
    @social_client_controller.get("/page", summary="获得社交客户端分页")
    @RoutePolicy(
        permissions=("system:social:client:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_social_client_page(
        page_req_vo: SocialClientPageReqVO = Query(),
        social_client_service: SocialClientService = Depends(DiDependency(SocialClientService)),
    ) -> Result[PageResult[SocialClientRespVO]]:
        page_result: PageResult[
            SocialClientDO
        ] = await social_client_service.get_social_client_page(page_req_vo)
        resp_vo: PageResult[SocialClientRespVO] = page_result.convert(SocialClientRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @social_client_controller.post("/send-subscribe-message", summary="发送订阅消息")
    @RoutePolicy(
        permissions=("system:social:client:send-subscribe-message",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def send_subscribe_message(
        req_vo: SubscribeMessageSendReqVO,
        social_client_api: SocialClientApi = Depends(DiDependency(SocialClientApi)),
    ) -> Result[bool]:
        await social_client_api.send_wxa_subscribe_message(
            SocialWxaSubscribeMessageSendReqDTO(**req_vo.model_dump(by_alias=False))
        )
        return Result.success(data=True)
