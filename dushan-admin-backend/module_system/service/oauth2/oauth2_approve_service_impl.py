from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Collection, override

from framework.common.dates import DateUtils
from framework.common.exception import ServiceException
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.config.system_settings import SystemSettings
from module_system.dal.dataobject.oauth2.oauth2_approve_do import OAuth2ApproveDO
from module_system.dal.mapper.oauth2.oauth2_approve_mapper import OAuth2ApproveMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.oauth2.oauth2_approve_service import OAuth2ApproveService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService


@service(interface=OAuth2ApproveService)
class OAuth2ApproveServiceImpl(OAuth2ApproveService):
    settings: SystemSettings = Inject()
    "OAuth2 授权批准服务实现类"
    approve_mapper: OAuth2ApproveMapper = Inject()
    client_service: OAuth2ClientService = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def check_for_pre_approval(
        self, user_id: int, user_type: int, client_id: str, requested_scopes: Collection[str]
    ) -> bool:
        client_dto: OAuth2ClientDTO = await self.client_service.validate_client(client_id)
        if not client_dto:
            raise ServiceException(ErrorCodeConstants.OAUTH2_CLIENT_NOT_EXISTS)
        auto_approve_scopes = set(client_dto.auto_approve_scopes or [])
        requested_scopes_list = list(requested_scopes)
        timeout = self.settings.approve_expire_seconds
        if auto_approve_scopes.issuperset(requested_scopes_list):
            expire_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                seconds=timeout
            )
            for scope in requested_scopes_list:
                await self.save_approve(user_id, user_type, client_id, scope, True, expire_time)
            return True
        approve_list = await self.get_approve_list(user_id, user_type, client_id)
        approved_scopes = {
            a.scope
            for a in approve_list
            if a.approved and (a.expires_time > datetime.now(timezone.utc).replace(tzinfo=None))
        }
        return all((scope in approved_scopes for scope in requested_scopes_list))

    @override
    @transactional
    async def update_after_approval(
        self, user_id: int, user_type: int, client_id: str, requested_scopes: dict[str, bool]
    ) -> bool:
        if not requested_scopes:
            return True
        timeout = self.settings.approve_expire_seconds
        expire_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=timeout)
        success = False
        for scope, approved in requested_scopes.items():
            if approved:
                success = True
            await self.save_approve(user_id, user_type, client_id, scope, approved, expire_time)
        return success

    @override
    async def get_approve_list(
        self, user_id: int, user_type: int, client_id: str
    ) -> list[OAuth2ApproveDO]:
        approves = await self.approve_mapper.select_list_by_user_id_and_user_type_and_client_id(
            user_id, user_type, client_id
        )
        return [
            a for a in approves if a.expires_time > datetime.now(timezone.utc).replace(tzinfo=None)
        ]

    @override
    async def save_approve(
        self,
        user_id: int,
        user_type: int,
        client_id: str,
        scope: str,
        approved: bool,
        expire_time: datetime,
    ) -> None:
        approve = OAuth2ApproveDO(
            user_id=user_id,
            user_type=user_type,
            client_id=client_id,
            scope=scope,
            approved=approved,
            expires_time=expire_time,
        )
        updated = await self.approve_mapper.update(approve)
        if updated == 0:
            await self.approve_mapper.insert(approve)
