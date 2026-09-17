from __future__ import annotations

from typing import override

from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.social.dto.social_wx_jsapi_signature_resp_dto import (
    SocialWxJsapiSignatureRespDTO,
)
from module_system.api.social.dto.social_wx_phone_number_info_resp_dto import (
    SocialWxPhoneNumberInfoRespDTO,
)
from module_system.api.social.dto.social_wx_qrcode_req_dto import SocialWxQrcodeReqDTO
from module_system.api.social.dto.social_wxa_order_notify_confirm_receive_req_dto import (
    SocialWxaOrderNotifyConfirmReceiveReqDTO,
)
from module_system.api.social.dto.social_wxa_order_upload_shipping_info_req_dto import (
    SocialWxaOrderUploadShippingInfoReqDTO,
)
from module_system.api.social.dto.social_wxa_subscribe_message_send_req_dto import (
    SocialWxaSubscribeMessageSendReqDTO,
)
from module_system.api.social.dto.social_wxa_subscribe_template_resp_dto import (
    SocialWxaSubscribeTemplateRespDTO,
)
from module_system.api.social.social_client_api import SocialClientApi
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.service.social.social_client_service import SocialClientService
from module_system.service.social.social_user_service import SocialUserService


@service(interface=SocialClientApi)
class SocialClientApiImpl(SocialClientApi):
    """社交应用 API 实现类"""

    social_client_service: SocialClientService = Inject()
    social_user_service: SocialUserService = Inject()

    @override
    async def get_authorize_url(self, social_type: int, user_type: int, redirect_uri: str) -> str:
        if not redirect_uri:
            raise ValueError("redirect_uri 不能为空")
        return await self.social_client_service.get_authorize_url(
            social_type, user_type, redirect_uri
        )

    @override
    async def create_wx_mp_jsapi_signature(
        self, user_type: int, url: str
    ) -> SocialWxJsapiSignatureRespDTO:
        if not url:
            raise ValueError("url 不能为空")
        signature_data = await self.social_client_service.create_wx_mp_jsapi_signature(
            user_type, url
        )
        return SocialWxJsapiSignatureRespDTO.model_validate(signature_data)

    @override
    async def get_wx_ma_phone_number_info(
        self, user_type: int, phone_code: str
    ) -> SocialWxPhoneNumberInfoRespDTO:
        if not phone_code:
            raise ValueError("phone_code 不能为空")
        info_data = await self.social_client_service.get_wx_ma_phone_number_info(
            user_type, phone_code
        )
        return SocialWxPhoneNumberInfoRespDTO.model_validate(info_data)

    @override
    async def get_wxa_qrcode(self, req_vo: SocialWxQrcodeReqDTO) -> bytes:
        return await self.social_client_service.get_wxa_qrcode(req_vo)

    @override
    async def get_wxa_subscribe_template_list(
        self, user_type: int
    ) -> list[SocialWxaSubscribeTemplateRespDTO]:
        template_list_data = await self.social_client_service.get_subscribe_template_list(user_type)
        return [
            SocialWxaSubscribeTemplateRespDTO.model_validate(
                {
                    "id": item.pri_tmpl_id,
                    "title": item.title,
                    "content": item.content,
                    "example": item.example,
                    "type": item.type,
                }
            )
            for item in template_list_data
        ]

    @override
    async def send_wxa_subscribe_message(
        self, req_dto: SocialWxaSubscribeMessageSendReqDTO
    ) -> None:
        template_list = await self.get_wxa_subscribe_template_list(req_dto.user_type)
        if not template_list:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_TEMPLATE_ERROR
            )
        template: SocialWxaSubscribeTemplateRespDTO | None = next(
            (item for item in template_list if item.title == req_dto.template_title), None
        )
        if template is None:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_TEMPLATE_ERROR
            )
        social_user = await self.social_user_service.get_social_user_by_user_id(
            req_dto.user_type, req_dto.user_id, SocialTypeEnum.WECHAT_MINI_PROGRAM.code
        )
        if not social_user or not social_user.openid:
            raise ServiceException(ErrorCodeConstants.SOCIAL_USER_NOT_FOUND)
        await self.social_client_service.send_subscribe_message(
            req_dto, template.id, social_user.openid
        )

    @override
    async def upload_wxa_order_shipping_info(
        self, user_type: int, req_dto: SocialWxaOrderUploadShippingInfoReqDTO
    ) -> None:
        await self.social_client_service.upload_wxa_order_shipping_info(user_type, req_dto)

    @override
    async def notify_wxa_order_confirm_receive(
        self, user_type: int, req_dto: SocialWxaOrderNotifyConfirmReceiveReqDTO
    ) -> None:
        await self.social_client_service.notify_wxa_order_confirm_receive(user_type, req_dto)
