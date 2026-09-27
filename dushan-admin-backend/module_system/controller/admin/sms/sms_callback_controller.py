from fastapi import APIRouter, Depends, Request

from framework.starter_di.public import DiDependency
from framework.starter_web.public import AccessLogPolicy, Result, RoutePolicy
from module_system.definitions.constants.public_contexts import PublicContexts
from module_system.service.sms.sms_send_service import SmsSendService

sms_callback_controller = APIRouter(prefix="/sms/callback", tags=["System - 短信回调管理"])


class SmsCallbackController:
    @staticmethod
    @sms_callback_controller.post("", summary="短信通道回执")
    @RoutePolicy.public(context=PublicContexts.SMS_CALLBACK)
    @AccessLogPolicy(enabled=False)
    async def receive_sms_status(
        request: Request,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
    ) -> Result[bool]:
        await sms_send_service.receive_sms_status(
            request.state.sms_callback_channel_id, (await request.body()).decode("utf-8")
        )
        return Result.success(True)
