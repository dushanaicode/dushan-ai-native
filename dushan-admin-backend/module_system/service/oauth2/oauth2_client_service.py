from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.controller.admin.oauth2.vo.client.oauth2_client_page_req_vo import (
    OAuth2ClientPageReqVO,
)
from module_system.controller.admin.oauth2.vo.client.oauth2_client_save_req_vo import (
    OAuth2ClientSaveReqVO,
)
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO


@runtime_checkable
class OAuth2ClientService(Protocol):
    async def create_oauth2_client(self, create_vo: OAuth2ClientSaveReqVO) -> int: ...

    async def update_oauth2_client(self, update_vo: OAuth2ClientSaveReqVO) -> None: ...

    async def update_status(self, client_id: int, status: int) -> None: ...

    async def delete_oauth2_client(self, client_id: int) -> None: ...

    async def delete_oauth2_client_batch(self, ids: list[int]) -> int: ...

    async def get_oauth2_client(self, id: int) -> OAuth2ClientDO | None: ...

    async def get_oauth2_client_from_cache(self, client_id: str) -> OAuth2ClientDTO | None: ...

    async def get_oauth2_client_page(
        self, page_vo: OAuth2ClientPageReqVO
    ) -> PageResult[OAuth2ClientDO]: ...

    async def validate_client(
        self,
        client_id: str,
        client_secret: str | None = None,
        grant_type: str | None = None,
        scopes: Collection[str] | None = None,
        redirect_uri: str | None = None,
    ) -> OAuth2ClientDTO: ...
