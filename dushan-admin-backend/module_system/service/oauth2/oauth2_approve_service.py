from __future__ import annotations

from datetime import datetime
from typing import Collection, Protocol, runtime_checkable

from module_system.dal.dataobject.oauth2.oauth2_approve_do import OAuth2ApproveDO


@runtime_checkable
class OAuth2ApproveService(Protocol):
    async def check_for_pre_approval(
        self, user_id: int, user_type: int, client_id: str, requested_scopes: Collection[str]
    ) -> bool: ...

    async def update_after_approval(
        self, user_id: int, user_type: int, client_id: str, requested_scopes: dict[str, bool]
    ) -> bool: ...

    async def get_approve_list(
        self, user_id: int, user_type: int, client_id: str
    ) -> list[OAuth2ApproveDO]: ...

    async def save_approve(
        self,
        user_id: int,
        user_type: int,
        client_id: str,
        scope: str,
        approved: bool,
        expire_time: datetime,
    ) -> None: ...
