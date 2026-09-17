from __future__ import annotations

import hmac
from typing import Collection, override

from sqlalchemy import select

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.decorators.cacheable import cache
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.controller.admin.oauth2.vo.client.oauth2_client_page_req_vo import (
    OAuth2ClientPageReqVO,
)
from module_system.controller.admin.oauth2.vo.client.oauth2_client_save_req_vo import (
    OAuth2ClientSaveReqVO,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO
from module_system.dal.mapper.oauth2.oauth2_client_mapper import OAuth2ClientMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService


@service(interface=OAuth2ClientService)
class OAuth2ClientServiceImpl(OAuth2ClientService):
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    "OAuth2 客户端服务实现类"
    oauth2_client_mapper: OAuth2ClientMapper = Inject()
    default_ttl: int = 3600

    @override
    @transactional
    async def create_oauth2_client(self, create_vo: OAuth2ClientSaveReqVO) -> int:
        await self._validate_client_id_unique(None, create_vo.client_id)
        client = OAuth2ClientDO(**create_vo.model_dump(by_alias=False))
        await self.oauth2_client_mapper.insert(client)
        return client.id

    @override
    @transactional
    async def update_oauth2_client(self, update_vo: OAuth2ClientSaveReqVO) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.OAUTH_CLIENT),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(update_vo.id)
        await self._validate_client_id_unique(update_vo.id, update_vo.client_id)
        client_in_db = await self.oauth2_client_mapper.select_by_id(update_vo.id)
        update_obj = OAuth2ClientDO(**update_vo.model_dump(by_alias=False))
        if not update_vo.secret:
            update_obj.secret = client_in_db.secret
        await self.oauth2_client_mapper.update_by_id(update_obj)
        await self.oauth2_client_mapper.update_by_condition(
            {"credential_revision": OAuth2ClientDO.credential_revision + 1},
            OAuth2ClientDO.id == update_obj.id,
        )

    @override
    @transactional
    async def update_status(self, client_id: int, status: int) -> None:
        """更新OAuth2客户端状态"""
        await self._validate_exists(client_id)
        update_obj = OAuth2ClientDO(id=client_id, status=status)
        await self.oauth2_client_mapper.update_by_id(update_obj)
        await self.oauth2_client_mapper.update_by_condition(
            {"credential_revision": OAuth2ClientDO.credential_revision + 1},
            OAuth2ClientDO.id == update_obj.id,
        )

    @override
    @transactional
    async def delete_oauth2_client(self, client_id: int) -> None:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.OAUTH_CLIENT),
            required=True,
            name="system-cache",
        )
        await self._validate_exists(client_id)
        await self.oauth2_client_mapper.delete_by_id(client_id)

    @override
    @transactional
    async def delete_oauth2_client_batch(self, ids: list[int]) -> int:
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(SystemCacheKeys.OAUTH_CLIENT),
            required=True,
            name="system-cache",
        )
        clients = await self.oauth2_client_mapper.select_by_ids(ids)
        if len(clients) != len(ids):
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_NOT_EXISTS)
        return await self.oauth2_client_mapper.delete_by_ids(ids)

    @override
    async def get_oauth2_client(self, id: int) -> OAuth2ClientDO | None:
        return await self.oauth2_client_mapper.select_by_id(id)

    @cache(
        SystemCacheKeys.OAUTH_CLIENT,
        key="client:{{client_id}}",
        ttl_seconds=default_ttl,
        unless=lambda result, *_, **__: not result is not None,
    )
    @override
    async def get_oauth2_client_from_cache(self, client_id: str) -> OAuth2ClientDTO | None:
        return await self.oauth2_client_mapper.select_details_dto_by_client_id(client_id)

    @override
    async def get_oauth2_client_page(
        self, page_vo: OAuth2ClientPageReqVO
    ) -> PageResult[OAuth2ClientDO]:
        return await self.oauth2_client_mapper.select_page(page_vo)

    @override
    async def validate_client(
        self,
        client_id: str,
        client_secret: str | None = None,
        grant_type: str | None = None,
        scopes: Collection[str] | None = None,
        redirect_uri: str | None = None,
    ) -> OAuth2ClientDTO:
        row = (
            await self.oauth2_client_mapper.read_from_primary(
                select(OAuth2ClientDO).where(OAuth2ClientDO.client_id == client_id)
            )
        ).scalar_one_or_none()
        client_dto = None if row is None else OAuth2ClientDTO.model_validate(row)
        if not client_dto:
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_NOT_EXISTS)
        if client_dto.status == StatusEnum.DISABLE.code:
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_DISABLE)
        if client_secret is not None and not hmac.compare_digest(client_secret, client_dto.secret):
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_CLIENT_SECRET_ERROR)
        if grant_type and grant_type not in (client_dto.authorized_grant_types or []):
            raise ServiceException(
                ErrorCodeConstants.OAUTH2_CLIENT_AUTHORIZED_GRANT_TYPE_NOT_EXISTS
            )
        if scopes and (not set(scopes).issubset(set(client_dto.scopes or []))):
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_SCOPE_OVER)
        if redirect_uri is not None and redirect_uri not in client_dto.redirect_uris:
            raise ServiceException(
                ErrorCodeConstants.OAUTH2_CLIENT_REDIRECT_URI_NOT_MATCH, msg=redirect_uri
            )
        return client_dto

    async def _validate_exists(self, client_id: int) -> None:
        """校验客户端是否存在"""
        if not await self.oauth2_client_mapper.select_by_id(client_id):
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_NOT_EXISTS)

    async def _validate_client_id_unique(self, id_: int | None, client_id: str) -> None:
        """校验 Client ID 是否被占用"""
        client = await self.oauth2_client_mapper.select_by_client_id(client_id)
        if client and (id_ is None or client.id != id_):
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_EXISTS)
