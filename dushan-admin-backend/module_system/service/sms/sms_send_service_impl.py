from __future__ import annotations

from typing import Any, override
from uuid import uuid4

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.exception import ServiceException
from framework.common.validator import Mobile
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum
from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.sms.factory.sms_client_factory import SmsClientFactory
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties
from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
from module_system.mq.message.sms.sms_send_message import SmsSendMessage
from module_system.mq.producer.sms.sms_producer_protocol import SmsProducerProtocol
from module_system.service.member.member_service import MemberService
from module_system.service.notification.notification_delivery_service import (
    NotificationDeliveryService,
)
from module_system.service.sms.bo.sms_dispatch_bo import SmsDispatchBO
from module_system.service.sms.bo.sms_log_create_bo import SmsLogCreateBO
from module_system.service.sms.bo.sms_receive_result_bo import SmsReceiveResultBO
from module_system.service.sms.bo.sms_send_bo import SmsSendBO
from module_system.service.sms.sms_channel_service import SmsChannelService
from module_system.service.sms.sms_log_service import SmsLogService
from module_system.service.sms.sms_send_service import SmsSendService
from module_system.service.sms.sms_template_service import SmsTemplateService
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=SmsSendService)
class SmsSendServiceImpl(SmsSendService):
    admin_user_service: AdminUserService = Inject()
    sms_channel_service: SmsChannelService = Inject()
    sms_template_service: SmsTemplateService = Inject()
    sms_log_service: SmsLogService = Inject()
    sms_client_factory: SmsClientFactory = Inject()
    sms_producer: SmsProducerProtocol = Inject()

    @override
    async def send_single_sms_to_admin(self, req: SmsSendBO) -> int:
        mobile = req.mobile
        if not mobile:
            user = await self._get_user(req.user_id)
            if user is not None:
                mobile = user.mobile
        return await self.send_single_sms(
            SmsDispatchBO(
                mobile=mobile,
                user_id=req.user_id,
                user_type=UserTypeEnum.ADMIN.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    @override
    @transactional
    async def send_single_sms(self, req: SmsDispatchBO) -> int:
        mobile = req.mobile
        template = await self._validate_sms_template(req.template_code)
        sms_channel = await self._validate_sms_channel(template.channel_id)
        mobile = self._validate_mobile(mobile)
        new_template_params = self._build_template_params(template, req.template_params)
        is_send = (
            template.status == StatusEnum.ENABLE.code
            and sms_channel.status == StatusEnum.ENABLE.code
        )
        if req.require_delivery and not is_send:
            if sms_channel.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_DISABLE)
            raise ServiceException(ErrorCodeConstants.SMS_TEMPLATE_DISABLED)
        content = self.sms_template_service.format_sms_template_content(
            template.content, req.template_params
        )
        send_log_id = await self.sms_log_service.create_sms_log(
            SmsLogCreateBO(
                mobile=mobile,
                user_id=req.user_id,
                user_type=req.user_type,
                is_send=is_send,
                template=template,
                template_content=content,
                template_params=new_template_params,
            )
        )
        if is_send:
            message_id = uuid4().hex
            await self.sms_producer.send_sms_message(
                SmsSendMessage(
                    message_id=message_id,
                    log_id=send_log_id,
                    mobile=mobile,
                    channel_id=template.channel_id,
                    api_template_id=template.api_template_id,
                    template_params=new_template_params,
                )
            )
        return send_log_id

    async def _validate_sms_channel(self, channel_id: int) -> SmsChannelDO:
        channel = await self.sms_channel_service.get_sms_channel(channel_id)
        if channel is None:
            raise ServiceException(ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS)
        return channel

    async def _validate_sms_template(self, template_code: str) -> SmsTemplateDO:
        template: SmsTemplateDO = await self.sms_template_service.get_sms_template_by_code(
            template_code
        )
        if template is None:
            raise ServiceException(ErrorCodeConstants.SMS_SEND_TEMPLATE_NOT_EXISTS)
        return template

    def _build_template_params(
        self, template: SmsTemplateDO, template_params: dict[str, Any]
    ) -> dict[str, Any]:
        if not template.params:
            return template_params
        validated_params: dict[str, Any] = {}
        for key in template.params:
            if key not in template_params:
                raise ServiceException(ErrorCodeConstants.SMS_SEND_MOBILE_TEMPLATE_PARAM_MISS, key)
            validated_params[key] = template_params[key]
        return validated_params

    async def _get_user(self, id: int) -> AdminUserDO | None:
        return await self.admin_user_service.get_user(id)

    delivery: NotificationDeliveryService = Inject()
    members: MemberService = Inject()

    async def do_send_sms(self, message: SmsSendMessage) -> None:
        """提供短信外发和厂商结果映射，投递状态由共享服务管理。"""
        channel_do = await self._validate_sms_channel(message.channel_id)
        channel = self.sms_client_factory.create_or_update_sms_client(
            SmsChannelProperties.model_validate(channel_do)
        )

        async def send_sms(on_request_started: DeliveryRequestStartedCallback) -> SmsSendRespDTO:
            """拒绝已停用渠道，并调用客户端的请求开始回调。"""
            if channel_do.status != StatusEnum.ENABLE.code:
                raise DeliveryCancelled("短信渠道已停用")
            return await channel.send_sms(
                message.log_id,
                message.mobile,
                message.api_template_id,
                message.template_params,
                on_request_started=on_request_started,
            )

        await self.delivery.execute(
            "sms",
            message.log_id,
            send=send_sms,
            result_values=lambda result: {
                "send_status": SmsSendStatusEnum.SUCCESS.code
                if result.success
                else SmsSendStatusEnum.FAILURE.code,
                "api_send_code": result.api_code,
                "api_send_msg": result.api_msg,
                "api_request_id": result.api_request_id,
                "api_serial_no": result.serial_no,
            },
        )

    async def send_single_sms_to_member(self, req: SmsSendBO):
        mobile = req.mobile
        if not mobile:
            mobile = await self.members.get_member_user_mobile(req.user_id)
        return await self.send_single_sms(
            SmsDispatchBO(
                mobile=mobile,
                user_id=req.user_id,
                user_type=UserTypeEnum.MEMBER.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    def _validate_mobile(self, mobile):
        if not mobile:
            raise ServiceException(ErrorCodeConstants.SMS_SEND_MOBILE_NOT_EXISTS)
        return Mobile.require_mobile("mobile", mobile)

    async def receive_sms_status(self, channel_id: int, text: str):
        channel = await self._validate_sms_channel(channel_id)
        client = self.sms_client_factory.create_or_update_sms_client(
            SmsChannelProperties.model_validate(channel)
        )
        for result in await client.parse_sms_receive_status(text):
            await self.sms_log_service.update_sms_receive_result(
                SmsReceiveResultBO(
                    id=result.log_id,
                    channel_id=channel_id,
                    success=result.success,
                    receive_time=result.receive_time,
                    api_receive_code=result.error_code,
                    api_receive_msg=result.error_msg,
                )
            )
