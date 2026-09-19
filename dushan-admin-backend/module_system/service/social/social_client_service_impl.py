from __future__ import annotations

import hashlib
import random
import string
import time
from typing import override

import httpx

from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_auth.public import (
    AuthClientProvider,
    AuthResult,
    AuthService,
)
from framework.starter_cache.public import CacheHandler
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
    SecuritySettings,
)
from framework.starter_web.public import (
    RequestContext,
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
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.social.social_client_do import SocialClientDO
from module_system.dal.mapper.social.social_client_mapper import SocialClientMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.framework.social.model.social_template_info import SocialTemplateInfo
from module_system.framework.social.model.social_wx_jsapi_signature import SocialWxJsapiSignature
from module_system.framework.social.model.social_wx_ma_phone_number_info import (
    SocialWxMaPhoneNumberInfo,
)
from module_system.framework.social.model.watermark import Watermark
from module_system.framework.social.security.social_auth_config_security import (
    SocialAuthConfigSecurity,
)
from module_system.service.social.social_client_service import SocialClientService


@service(interface=SocialClientService)
class SocialClientServiceImpl(SocialClientService):
    social_client_mapper: SocialClientMapper = Inject()
    cache_handler: CacheHandler = Inject()
    CACHE_PREFIX_SOCIAL_CLIENT = "social_client"
    CACHE_TTL_SOCIAL_CLIENT = 3600
    WXA_CODE_ENV_VERSION = "release"
    WXA_SUBSCRIBE_MESSAGE_STATE = "formal"

    async def _get_client_config(self, social_type: int, user_type: int) -> SocialClientDO:
        client_do = await self.social_client_mapper.select_by_social_type_and_user_type(
            social_type, user_type
        )
        if not client_do:
            raise ServiceException(ErrorCodeConstants.SOCIAL_CLIENT_NOT_EXISTS)
        return client_do

    @override
    @transactional
    async def create_wx_mp_jsapi_signature(
        self, user_type: int, url: str
    ) -> SocialWxJsapiSignature:
        client_config = await self._get_client_config(SocialTypeEnum.WECHAT_MP.code, user_type)
        jsapi_ticket = await self._get_jsapi_ticket(client_config)
        noncestr = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        timestamp = int(time.time())
        signature_str = (
            f"jsapi_ticket={jsapi_ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}"
        )
        signature = hashlib.sha1(signature_str.encode("utf-8")).hexdigest()
        return SocialWxJsapiSignature(
            app_id=client_config.client_id,
            timestamp=timestamp,
            nonce_str=noncestr,
            signature=signature,
            url=url,
        )

    async def _get_jsapi_ticket(self, client_config: SocialClientDO) -> str:
        cache_key = f"jsapi_ticket:{client_config.client_id}"

        async def ticket_loader():
            access_token = await self._get_access_token(client_config)
            url = f"https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi"
            async with httpx.AsyncClient(timeout=30) as session:
                response = await session.get(url)
                response.raise_for_status()
                result = response.json()
            if result.get("errcode") != 0:
                raise ServiceException(
                    ErrorCodeConstants.SOCIAL_WECHAT_MP_JS_SDK_SIGNATURE_ERROR,
                    result.get("errmsg", "未知错误"),
                )
            return result.get("ticket")

        return await self.cache_handler.get_or_load(
            SystemCacheKeys.SOCIAL_CLIENT, cache_key, ticket_loader, ttl_seconds=7200
        )

    async def _get_access_token(self, client_config: SocialClientDO) -> str:
        cache_key = f"access_token:{client_config.client_id}"

        async def token_loader():
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={client_config.client_id}&secret={client_config.client_secret}"
            async with httpx.AsyncClient(timeout=30) as session:
                response = await session.get(url)
                response.raise_for_status()
                result = response.json()
            if "access_token" not in result:
                raise ServiceException(
                    ErrorCodeConstants.SOCIAL_CLIENT_AUTH_FAILURE, result.get("errmsg", "未知错误")
                )
            return result.get("access_token")

        return await self.cache_handler.get_or_load(
            SystemCacheKeys.SOCIAL_CLIENT, cache_key, token_loader, ttl_seconds=7200
        )

    @override
    async def get_wx_ma_phone_number_info(
        self, user_type: int, phone_code: str
    ) -> SocialWxMaPhoneNumberInfo:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, user_type
        )
        access_token = await self._get_access_token(client_config)
        url = (
            f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}"
        )
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.post(url, json={"code": phone_code})
            response.raise_for_status()
            result = response.json()
        if result.get("errcode") != 0:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_PHONE_CODE_ERROR,
                result.get("errmsg", "未知错误"),
            )
        phone_info = result.get("phone_info", {})
        watermark_data = phone_info.get("watermark", {})
        watermark = Watermark(
            timestamp=watermark_data.get("timestamp", 0), appid=watermark_data.get("appid", "")
        )
        return SocialWxMaPhoneNumberInfo(
            phone_number=phone_info.get("phoneNumber", ""),
            pure_phone_number=phone_info.get("purePhoneNumber", ""),
            country_code=phone_info.get("countryCode", ""),
            watermark=watermark,
        )

    @override
    async def get_wxa_qrcode(self, req_vo: SocialWxQrcodeReqDTO) -> bytes:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, req_vo.user_type
        )
        access_token = await self._get_access_token(client_config)
        data = {
            "scene": req_vo.scene or "default",
            "page": req_vo.path,
            "check_path": req_vo.check_path if req_vo.check_path is not None else True,
            "env_version": self.WXA_CODE_ENV_VERSION,
            "width": req_vo.width or 430,
            "auto_color": req_vo.auto_color if req_vo.auto_color is not None else False,
            "is_hyaline": req_vo.hyaline if req_vo.hyaline is not None else False,
        }
        url = f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}"
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.post(url, json=data)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                result = response.json()
                raise ServiceException(
                    ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_QRCODE_ERROR,
                    result.get("errmsg", "未知错误"),
                )
            return response.content

    @override
    async def get_subscribe_template_list(self, user_type: int) -> list[SocialTemplateInfo]:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, user_type
        )
        access_token = await self._get_access_token(client_config)
        url = f"https://api.weixin.qq.com/wxaapi/newtmpl/gettemplate?access_token={access_token}"
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.get(url)
            response.raise_for_status()
            result = response.json()
        if result.get("errcode") != 0:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_TEMPLATE_ERROR,
                result.get("errmsg", "未知错误"),
            )
        return [
            SocialTemplateInfo(
                pri_tmpl_id=item.get("priTmplId", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                example=item.get("example", ""),
                type=item.get("type", 0),
            )
            for item in result.get("data", [])
        ]

    @override
    async def send_subscribe_message(
        self, req_dto: SocialWxaSubscribeMessageSendReqDTO, template_id: str, openid: str
    ) -> None:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, req_dto.user_type
        )
        access_token = await self._get_access_token(client_config)
        message_data = {}
        if req_dto.messages:
            for key, value in req_dto.messages.items():
                message_data[key] = {"value": value}
        data = {
            "touser": openid,
            "template_id": template_id,
            "page": req_dto.page,
            "miniprogram_state": self.WXA_SUBSCRIBE_MESSAGE_STATE,
            "lang": "zh_CN",
            "data": message_data,
        }
        url = (
            f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        )
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.post(url, json=data)
            response.raise_for_status()
            result = response.json()
        if result.get("errcode") != 0:
            if result.get("errcode") == 43101:
                return
            error_msg = result.get("errmsg", "未知错误")
            if result.get("errcode") == 47003:
                error_msg = "模板已被禁用或下线"
            elif result.get("errcode") == 41030:
                error_msg = "跳转的小程序页面路径无效"
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_MESSAGE_ERROR, error_msg
            )

    @override
    async def upload_wxa_order_shipping_info(
        self, user_type: int, req_dto: SocialWxaOrderUploadShippingInfoReqDTO
    ) -> None:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, user_type
        )
        access_token = await self._get_access_token(client_config)
        data = {
            "order_key": {"order_number_type": 2, "transaction_id": req_dto.transaction_id},
            "logistics_type": req_dto.logistics_type,
            "delivery_mode": 1,
            "shipping_list": self._build_wxa_shipping_list(req_dto),
            "payer": {"openid": req_dto.openid},
            "receiver_contact": req_dto.receiver_contact,
            "item_desc": req_dto.item_desc,
        }
        url = f"https://api.weixin.qq.com/wxa/sec/order/upload_shipping_info?access_token={access_token}"
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.post(url, json=data)
            response.raise_for_status()
            result = response.json()
        if result.get("errcode") != 0:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_ORDER_SHIPPING_ERROR,
                result.get("errmsg", "未知错误"),
            )

    @override
    async def notify_wxa_order_confirm_receive(
        self, user_type: int, req_dto: SocialWxaOrderNotifyConfirmReceiveReqDTO
    ) -> None:
        client_config = await self._get_client_config(
            SocialTypeEnum.WECHAT_MINI_PROGRAM.code, user_type
        )
        access_token = await self._get_access_token(client_config)
        data = {
            "transaction_id": req_dto.transaction_id,
            "received_time": int(req_dto.received_time.timestamp()),
        }
        url = f"https://api.weixin.qq.com/wxa/sec/order/notify_confirm_receive?access_token={access_token}"
        async with httpx.AsyncClient(timeout=30) as session:
            response = await session.post(url, json=data)
            response.raise_for_status()
            result = response.json()
        if result.get("errcode") != 0:
            raise ServiceException(
                ErrorCodeConstants.SOCIAL_CLIENT_WEIXIN_MINI_APP_ORDER_CONFIRM_RECEIVE_ERROR,
                result.get("errmsg", "未知错误"),
            )

    @staticmethod
    def _build_wxa_shipping_list(
        req_dto: SocialWxaOrderUploadShippingInfoReqDTO,
    ) -> list[dict[str, str]]:
        if req_dto.logistics_no and req_dto.express_company:
            return [
                {"tracking_no": req_dto.logistics_no, "express_company": req_dto.express_company}
            ]
        return []

    async def _validate_social_client_exists(self, client_id: int) -> SocialClientDO:
        client = await self.social_client_mapper.select_by_id(client_id)
        if not client:
            raise ServiceException(ErrorCodeConstants.SOCIAL_CLIENT_NOT_EXISTS)
        return client

    async def _validate_social_client_unique(
        self, client_id: int | None, user_type: int, social_type: int
    ) -> None:
        client = await self.social_client_mapper.select_by_social_type_and_user_type(
            social_type, user_type
        )
        if client is None:
            return
        if client_id is None or client.id != client_id:
            social_type_enum = SocialTypeEnum.get_by_code(social_type)
            type_name = social_type_enum.label if social_type_enum else f"类型{social_type}"
            raise ServiceException(ErrorCodeConstants.SOCIAL_CLIENT_UNIQUE, type_name)

    @override
    @transactional
    async def create_social_client(self, create_req_vo: SocialClientSaveReqVO) -> int:
        await self._validate_social_client_unique(
            None, create_req_vo.user_type, create_req_vo.social_type
        )
        client_do = SocialClientDO(**create_req_vo.model_dump(exclude_unset=True, by_alias=False))
        inserted_client = await self.social_client_mapper.insert(client_do)
        return inserted_client.id

    @override
    @transactional
    async def update_social_client(self, update_req_vo: SocialClientSaveReqVO) -> None:
        existing = await self._validate_social_client_exists(update_req_vo.id)
        await self._validate_social_client_unique(
            update_req_vo.id, update_req_vo.user_type, update_req_vo.social_type
        )
        values = update_req_vo.model_dump(exclude_unset=True, by_alias=False)
        if "auth_config" in values:
            SocialAuthConfigSecurity.validate_auth_config_secret_values(values["auth_config"])
            values["auth_config"] = SocialAuthConfigSecurity.merge_preserved_auth_config_secrets(
                existing.auth_config, values["auth_config"]
            )
        update_obj = SocialClientDO(**values)
        await self.social_client_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, client_id: int, status: int) -> None:
        """更新社交客户端状态"""
        await self._validate_social_client_exists(client_id)
        update_obj = SocialClientDO(id=client_id, status=status)
        await self.social_client_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_social_client(self, client_id: int) -> None:
        await self._validate_social_client_exists(client_id)
        await self.social_client_mapper.delete_by_id(client_id)

    @override
    @transactional
    async def delete_social_client_batch(self, ids: list[int]) -> int:
        if not ids:
            return 0
        for client_id in ids:
            await self._validate_social_client_exists(client_id)
        return await self.social_client_mapper.delete_by_ids(ids)

    @override
    async def get_social_client(self, client_id: int) -> SocialClientDO | None:
        return await self.social_client_mapper.select_by_id(client_id)

    @override
    async def get_social_client_page(
        self, page_req_vo: SocialClientPageReqVO
    ) -> PageResult[SocialClientDO]:
        return await self.social_client_mapper.select_page(page_req_vo)

    @override
    async def get_enabled_social_clients(self) -> list[SocialClientDO]:
        return await self.social_client_mapper.select_list_by_status()

    @override
    async def get_social_client_by_type(
        self, social_type: int, user_type: int | None
    ) -> SocialClientDO | None:
        return await self.social_client_mapper.select_by_social_type_and_user_type(
            social_type, user_type
        )

    auth: AuthService = Inject()
    settings: SecuritySettings = Inject()
    clients: AuthClientProvider = Inject()

    def _application_id(self, user_type):
        suffix = {1: "member", 2: "admin"}[user_type]
        return f"{self.settings.application_id}-{suffix}"

    def _get_source_type(self, social_type):
        source = SocialTypeEnum.from_code(social_type).label
        return "WECHAT_ENTERPRISE_WEB" if source == "WECHAT_ENTERPRISE_V2" else source

    async def get_authorize_url(self, social_type, user_type, redirect_uri, *, binding):
        application = self._application_id(user_type)
        source = self._get_source_type(social_type)
        client = await self.clients.get_client(application, source)
        if client is None or redirect_uri != client.redirect_uri:
            raise SecurityException(SecurityErrorCodes.INVALID)
        authorization = await self.auth.begin(application, source, binding=binding)
        return authorization

    async def get_auth_user(self, social_type, user_type, code, state) -> AuthResult:
        binding = RequestContext.current().connection.cookies.get("system_social_binding")
        if binding is None:
            raise SecurityException(SecurityErrorCodes.INVALID)
        return await self.auth.complete(
            self._application_id(user_type),
            self._get_source_type(social_type),
            [("code", code), ("state", state)],
            binding=binding,
        )
