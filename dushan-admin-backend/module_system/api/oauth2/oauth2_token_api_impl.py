from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.oauth2.dto.oauth2_access_token_check_resp_dto import (
    OAuth2AccessTokenCheckRespDTO,
)
from module_system.api.oauth2.dto.oauth2_access_token_create_req_dto import (
    OAuth2AccessTokenCreateReqDTO,
)
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.api.oauth2.oauth2_token_api import OAuth2TokenApi
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=OAuth2TokenApi)
class OAuth2TokenApiImpl(OAuth2TokenApi):
    """OAuth2.0 令牌 API 实现类"""

    oauth2_token_service: OAuth2TokenService = Inject()

    @override
    async def create_access_token(
        self, req_dto: OAuth2AccessTokenCreateReqDTO
    ) -> OAuth2AccessTokenRespDTO:
        access_token_do = await self.oauth2_token_service.create_access_token(
            req_dto.user_id, req_dto.user_type, req_dto.client_id, req_dto.scopes
        )
        return OAuth2AccessTokenRespDTO.model_validate(access_token_do)

    @override
    async def check_access_token(self, access_token: str) -> OAuth2AccessTokenCheckRespDTO:
        if not access_token:
            raise ValueError("access_token 不能为空")
        access_token_do = await self.oauth2_token_service.check_access_token(access_token)
        return OAuth2AccessTokenCheckRespDTO.model_validate(access_token_do)

    @override
    async def remove_access_token(self, access_token: str) -> OAuth2AccessTokenCheckRespDTO | None:
        if not access_token:
            raise ValueError("access_token 不能为空")
        access_token_do = await self.oauth2_token_service.remove_access_token(access_token)
        if not access_token_do:
            return None
        return OAuth2AccessTokenCheckRespDTO.model_validate(access_token_do)

    @override
    async def refresh_access_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO:
        if not refresh_token:
            raise ValueError("refresh_token 不能为空")
        if not client_id:
            raise ValueError("client_id 不能为空")
        access_token_do = await self.oauth2_token_service.refresh_access_token(
            refresh_token, client_id
        )
        return OAuth2AccessTokenRespDTO.model_validate(access_token_do)
