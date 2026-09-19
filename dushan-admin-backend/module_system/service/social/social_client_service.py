from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from framework.starter_auth.public import (
    AuthResult,
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
from module_system.controller.admin.social.vo.client.social_client_page_req_vo import (
    SocialClientPageReqVO,
)
from module_system.controller.admin.social.vo.client.social_client_save_req_vo import (
    SocialClientSaveReqVO,
)
from module_system.dal.dataobject.social.social_client_do import SocialClientDO
from module_system.framework.social.model.social_template_info import SocialTemplateInfo
from module_system.framework.social.model.social_wx_jsapi_signature import SocialWxJsapiSignature
from module_system.framework.social.model.social_wx_ma_phone_number_info import (
    SocialWxMaPhoneNumberInfo,
)


@runtime_checkable
class SocialClientService(Protocol):
    async def create_wx_mp_jsapi_signature(
        self, user_type: int, url: str
    ) -> SocialWxJsapiSignature: ...

    async def get_wx_ma_phone_number_info(
        self, user_type: int, phone_code: str
    ) -> SocialWxMaPhoneNumberInfo: ...

    async def get_wxa_qrcode(self, req_vo: SocialWxQrcodeReqDTO) -> bytes: ...

    async def get_subscribe_template_list(self, user_type: int) -> list[SocialTemplateInfo]: ...

    async def send_subscribe_message(
        self, req_dto: SocialWxaSubscribeMessageSendReqDTO, template_id: str, openid: str
    ) -> None: ...

    async def upload_wxa_order_shipping_info(
        self, user_type: int, req_dto: SocialWxaOrderUploadShippingInfoReqDTO
    ) -> None: ...

    async def notify_wxa_order_confirm_receive(
        self, user_type: int, req_dto: SocialWxaOrderNotifyConfirmReceiveReqDTO
    ) -> None: ...

    async def create_social_client(self, create_req_vo: SocialClientSaveReqVO) -> int: ...

    async def update_social_client(self, update_req_vo: SocialClientSaveReqVO) -> None: ...

    async def update_status(self, client_id: int, status: int) -> None: ...

    async def delete_social_client(self, client_id: int) -> None: ...

    async def delete_social_client_batch(self, ids: list[int]) -> int: ...

    async def get_social_client(self, client_id: int) -> SocialClientDO | None: ...

    async def get_social_client_page(
        self, page_req_vo: SocialClientPageReqVO
    ) -> PageResult[SocialClientDO]: ...

    async def get_enabled_social_clients(self) -> list[SocialClientDO]: ...

    async def get_social_client_by_type(
        self, social_type: int, user_type: int | None
    ) -> SocialClientDO | None: ...

    async def get_authorize_url(self, social_type, user_type, redirect_uri, *, binding): ...

    async def get_auth_user(self, social_type, user_type, code, state) -> AuthResult: ...
