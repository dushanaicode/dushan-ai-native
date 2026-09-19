from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.api.social.dto.social_user_unbind_req_dto import SocialUserUnbindReqDTO
from module_system.api.social.social_user_api import SocialUserApi
from module_system.service.social.social_user_service import SocialUserService


@service(interface=SocialUserApi)
class SocialUserApiImpl(SocialUserApi):
    social_user_service: SocialUserService = Inject()

    @override
    async def bind_social_user(self, req_dto: SocialUserBindReqDTO) -> str:
        """绑定社交用户"""
        return await self.social_user_service.bind_social_user(req_dto)

    @override
    async def unbind_social_user(self, req_dto: SocialUserUnbindReqDTO) -> None:
        """解绑社交用户"""
        await self.social_user_service.unbind_social_user(
            req_dto.user_id, req_dto.user_type, req_dto.social_type, req_dto.openid
        )

    @override
    async def get_social_user_by_user_id(
        self, user_type: int, user_id: int, social_type: int
    ) -> SocialUserRespDTO:
        """通过用户ID获取社交用户信息"""
        return await self.social_user_service.get_social_user_by_user_id(
            user_type, user_id, social_type
        )

    @override
    async def get_social_user_by_code(
        self, user_type: int, social_type: int, code: str, state: str
    ) -> SocialUserRespDTO:
        """通过授权码获取社交用户信息"""
        if not code:
            raise ValueError("code 不能为空")
        if not state:
            raise ValueError("state 不能为空")
        return await self.social_user_service.get_social_user_by_code(
            user_type, social_type, code, state
        )
