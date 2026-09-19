from fastapi import APIRouter, Depends, Query

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_system.controller.admin.sms.vo.channel.channel_page_req_vo import SmsChannelPageReqVO
from module_system.controller.admin.sms.vo.channel.channel_resp_vo import SmsChannelRespVO
from module_system.controller.admin.sms.vo.channel.channel_save_req_vo import SmsChannelSaveReqVO
from module_system.controller.admin.sms.vo.channel.channel_simple_resp_vo import (
    SmsChannelSimpleRespVO,
)
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.service.sms.sms_channel_service import SmsChannelService

sms_channel_controller = APIRouter(prefix="/sms/channel", tags=["System - 短信渠道管理"])


class SmsChannelController:
    @staticmethod
    @sms_channel_controller.post("/create", summary="创建短信渠道")
    @RoutePolicy(
        permissions=("system:sms:channel:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_sms_channel(
        create_req_vo: SmsChannelSaveReqVO,
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[SnowflakeIdStr]:
        channel_id = await sms_channel_service.create_sms_channel(create_req_vo)
        return Result.success(data=channel_id)

    @staticmethod
    @sms_channel_controller.put("/update", summary="更新短信渠道")
    @RoutePolicy(
        permissions=("system:sms:channel:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_sms_channel(
        update_req_vo: SmsChannelSaveReqVO,
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[bool]:
        await sms_channel_service.update_sms_channel(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @sms_channel_controller.put("/update-status", summary="修改短信渠道状态")
    @RoutePolicy(
        permissions=("system:sms:channel:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @sms_channel_controller.delete("/delete", summary="删除短信渠道")
    @RoutePolicy(
        permissions=("system:sms:channel:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_sms_channel(
        req_vo: IdReqVO = Query(),
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[bool]:
        await sms_channel_service.delete_sms_channel(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @sms_channel_controller.delete("/delete-list", summary="批量删除短信渠道")
    @RoutePolicy(
        permissions=("system:sms:channel:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_sms_channel_batch(
        req_vo: IdListReqVO = Query(),
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[int]:
        deleted_count = await sms_channel_service.delete_sms_channel_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @sms_channel_controller.get("/get", summary="获得短信渠道")
    @RoutePolicy(
        permissions=("system:sms:channel:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_sms_channel(
        req_vo: IdReqVO = Query(),
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[SmsChannelRespVO]:
        channel = await sms_channel_service.get_sms_channel(req_vo.id)
        if channel is None:
            return Result.success(data=None)
        data = SmsChannelRespVO.model_validate(channel)
        return Result.success(data=data)

    @staticmethod
    @sms_channel_controller.get("/page", summary="获得短信渠道分页")
    @RoutePolicy(
        permissions=("system:sms:channel:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_sms_channel_page(
        page_req_vo: SmsChannelPageReqVO = Query(),
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[PageResult[SmsChannelRespVO]]:
        page_result: PageResult[SmsChannelDO] = await sms_channel_service.get_sms_channel_page(
            page_req_vo
        )
        resp_vo: PageResult[SmsChannelRespVO] = page_result.convert(SmsChannelRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @sms_channel_controller.get("/simple-list", summary="获得短信渠道精简列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_sms_channel_list(
        sms_channel_service: SmsChannelService = Depends(DiDependency(SmsChannelService)),
    ) -> Result[list[SmsChannelSimpleRespVO]]:
        channels = await sms_channel_service.get_sms_channel_list()
        channels.sort(key=lambda c: c.id)
        data = [SmsChannelSimpleRespVO.model_validate(channel) for channel in channels]
        return Result.success(data=data)
