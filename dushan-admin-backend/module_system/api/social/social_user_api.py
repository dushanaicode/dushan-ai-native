from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.api.social.dto.social_user_unbind_req_dto import SocialUserUnbindReqDTO


@runtime_checkable
class SocialUserApi(Protocol):
    """社交用户 API 接口"""

    async def bind_social_user(self, req_dto: SocialUserBindReqDTO) -> str:
        """绑定社交用户"""
        ...

    async def unbind_social_user(self, req_dto: SocialUserUnbindReqDTO) -> None:
        """解绑社交用户"""
        ...

    async def get_social_user_by_user_id(
        self, user_type: int, user_id: int, social_type: int
    ) -> SocialUserRespDTO:
        """通过用户ID获取社交用户信息"""
        ...

    async def get_social_user_by_code(
        self, user_type: int, social_type: int, code: str, state: str
    ) -> SocialUserRespDTO:
        """通过授权码获取社交用户信息"""
        ...
