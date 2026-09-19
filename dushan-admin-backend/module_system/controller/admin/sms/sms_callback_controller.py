import hmac

from fastapi import APIRouter, Depends, Request

from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_system.config.system_settings import SystemSettings
from module_system.framework.sms.enums.sms_channel_enum import SmsChannelEnum
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.sms.sms_send_service import SmsSendService

sms_callback_controller = APIRouter(prefix="/sms/callback", tags=["System - 短信回调管理"])


class SmsCallbackController:
    @staticmethod
    @sms_callback_controller.post("/aliyun", summary="阿里云短信的回调")
    @RoutePolicy.public()
    async def receive_aliyun_sms_status(
        request: Request,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        token = request.query_params.get("token")
        if settings.sms_callback_token is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if token is None or not hmac.compare_digest(
            token, settings.sms_callback_token.get_secret_value()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID, detail="回调令牌不匹配")
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            body_bytes = await request.body()
            text = body_bytes.decode("utf-8")
            await sms_send_service.receive_sms_status(SmsChannelEnum.ALIYUN.code, text)
            return Result.success(data=True)

    @staticmethod
    @sms_callback_controller.post("/tencent", summary="腾讯云短信的回调")
    @RoutePolicy.public()
    async def receive_tencent_sms_status(
        request: Request,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        token = request.query_params.get("token")
        if settings.sms_callback_token is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if token is None or not hmac.compare_digest(
            token, settings.sms_callback_token.get_secret_value()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID, detail="回调令牌不匹配")
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            body_bytes = await request.body()
            text = body_bytes.decode("utf-8")
            await sms_send_service.receive_sms_status(SmsChannelEnum.TENCENT.code, text)
            return Result.success(data=True)

    @staticmethod
    @sms_callback_controller.post("/huawei", summary="华为云短信的回调")
    @RoutePolicy.public()
    async def receive_huawei_sms_status(
        request: Request,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        token = request.query_params.get("token")
        if settings.sms_callback_token is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if token is None or not hmac.compare_digest(
            token, settings.sms_callback_token.get_secret_value()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID, detail="回调令牌不匹配")
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            body_bytes = await request.body()
            text = body_bytes.decode("utf-8")
            await sms_send_service.receive_sms_status(SmsChannelEnum.HUAWEI.code, text)
            return Result.success(data=True)

    @staticmethod
    @sms_callback_controller.post("/qiniu", summary="七牛云短信的回调")
    @RoutePolicy.public()
    async def receive_qiniu_sms_status(
        request: Request,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        token = request.query_params.get("token")
        if settings.sms_callback_token is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if token is None or not hmac.compare_digest(
            token, settings.sms_callback_token.get_secret_value()
        ):
            raise SecurityException(SecurityErrorCodes.INVALID, detail="回调令牌不匹配")
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            body_bytes = await request.body()
            text = body_bytes.decode("utf-8")
            await sms_send_service.receive_sms_status(SmsChannelEnum.QINIU.code, text)
            return Result.success(data=True)
