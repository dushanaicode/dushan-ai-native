from __future__ import annotations

from typing import Protocol, runtime_checkable

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


@runtime_checkable
class SocialClientApi(Protocol):
    """社交应用 API 接口"""

    async def get_authorize_url(self, social_type: int, user_type: int, redirect_uri: str) -> str:
        """获取授权 URL"""
        ...

    async def create_wx_mp_jsapi_signature(
        self, user_type: int, url: str
    ) -> SocialWxJsapiSignatureRespDTO:
        """创建微信公众号 JSAPI 签名"""
        ...

    async def get_wx_ma_phone_number_info(
        self, user_type: int, phone_code: str
    ) -> SocialWxPhoneNumberInfoRespDTO:
        """获取微信小程序手机号码信息"""
        ...

    async def get_wxa_qrcode(self, req_vo: SocialWxQrcodeReqDTO) -> bytes:
        """获取微信小程序二维码"""
        ...

    async def get_wxa_subscribe_template_list(
        self, user_type: int
    ) -> list[SocialWxaSubscribeTemplateRespDTO]:
        """获取微信小程序订阅模板列表"""
        ...

    async def send_wxa_subscribe_message(
        self, req_dto: SocialWxaSubscribeMessageSendReqDTO
    ) -> None:
        """发送微信小程序订阅消息"""
        ...

    async def upload_wxa_order_shipping_info(
        self, user_type: int, req_dto: SocialWxaOrderUploadShippingInfoReqDTO
    ) -> None:
        """上传微信小程序订单物流信息"""
        ...

    async def notify_wxa_order_confirm_receive(
        self, user_type: int, req_dto: SocialWxaOrderNotifyConfirmReceiveReqDTO
    ) -> None:
        """通知微信小程序订单确认收货"""
        ...
