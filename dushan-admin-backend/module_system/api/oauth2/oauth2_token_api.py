from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.oauth2.dto.oauth2_access_token_check_resp_dto import (
    OAuth2AccessTokenCheckRespDTO,
)
from module_system.api.oauth2.dto.oauth2_access_token_create_req_dto import (
    OAuth2AccessTokenCreateReqDTO,
)
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO


@runtime_checkable
class OAuth2TokenApi(Protocol):
    """OAuth2.0 令牌 API 接口"""

    async def create_access_token(
        self, req_dto: OAuth2AccessTokenCreateReqDTO
    ) -> OAuth2AccessTokenRespDTO:
        """创建访问令牌"""
        ...

    async def check_access_token(self, access_token: str) -> OAuth2AccessTokenCheckRespDTO:
        """检查访问令牌"""
        ...

    async def remove_access_token(self, access_token: str) -> OAuth2AccessTokenCheckRespDTO | None:
        """移除访问令牌"""
        ...

    async def refresh_access_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO:
        """刷新访问令牌"""
        ...
