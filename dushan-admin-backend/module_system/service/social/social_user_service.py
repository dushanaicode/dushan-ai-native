from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.controller.admin.social.vo.user.user_page_req_vo import SocialUserPageReqVO
from module_system.dal.dataobject.social.social_user_do import SocialUserDO


@runtime_checkable
class SocialUserService(Protocol):
    async def get_social_user_list(self, user_id: int, user_type: int) -> list[SocialUserDO]: ...

    async def bind_social_user(self, req: SocialUserBindReqDTO) -> str: ...

    async def unbind_social_user(
        self, user_id: int, user_type: int, social_type: int, openid: str
    ) -> None: ...

    async def get_social_user_by_user_id(
        self, user_type: int, user_id: int, social_type: int
    ) -> SocialUserRespDTO | None: ...

    async def get_social_user_by_code(
        self, user_type: int, social_type: int, code: str, state: str
    ) -> SocialUserRespDTO | None: ...

    async def get_social_user_page(self, req: SocialUserPageReqVO) -> PageResult[SocialUserDO]: ...

    async def get_social_user(self, social_user_id: int) -> SocialUserDO | None: ...
