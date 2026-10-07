from __future__ import annotations

from typing import override

from sqlalchemy import select

from framework.common.enums import UserTypeEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.common.utils import JsonUtils
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.controller.admin.social.vo.user.social_user_page_req_vo import (
    SocialUserPageReqVO,
)
from module_system.dal.dataobject.social.social_user_bind_do import SocialUserBindDO
from module_system.dal.dataobject.social.social_user_do import SocialUserDO
from module_system.dal.mapper.social.social_user_bind_mapper import SocialUserBindMapper
from module_system.dal.mapper.social.social_user_mapper import SocialUserMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.permission.role_code_enum import RoleCodeEnum
from module_system.service.permission.permission_service import PermissionService
from module_system.service.social.social_client_service import SocialClientService
from module_system.service.social.social_user_service import SocialUserService


@service(interface=SocialUserService)
class SocialUserServiceImpl(SocialUserService):
    social_user_mapper: SocialUserMapper = Inject()
    social_user_bind_mapper: SocialUserBindMapper = Inject()
    social_client_service: SocialClientService = Inject()
    permission_service: PermissionService = Inject()

    @override
    async def get_social_user_list(self, user_id: int, user_type: int) -> list[SocialUserDO]:
        social_user_binds = await self.social_user_bind_mapper.select_list_by_user_id_and_user_type(
            user_id, user_type
        )
        if not social_user_binds:
            return []
        user_ids = [bind.social_user_id for bind in social_user_binds]
        return await self.social_user_mapper.select_batch_ids(user_ids)

    @override
    @transactional
    async def bind_social_user(self, req: SocialUserBindReqDTO) -> str:
        if req.user_type == UserTypeEnum.ADMIN.code:
            await self.permission_service.require_user_writable(req.user_id)
        social_user = await self._auth_social_user(req.type, req.user_type, req.code, req.state)
        if not social_user:
            raise ServiceException(ErrorCodeConstants.SOCIAL_USER_NOT_FOUND)
        existing = await self.social_user_bind_mapper.select_by_user_type_and_social_user_id(
            req.user_type, social_user.id
        )
        if existing is not None and existing.user_id != req.user_id:
            raise ServiceException(ErrorCodeConstants.SOCIAL_USER_ALREADY_BOUND)
        await self.social_user_bind_mapper.delete_by_user_type_and_social_user_id(
            req.user_type, social_user.id
        )
        await self.social_user_bind_mapper.delete_by_user_type_and_user_id_and_social_type(
            req.user_type, req.user_id, social_user.type
        )
        social_user_bind = SocialUserBindDO(
            user_id=req.user_id,
            user_type=req.user_type,
            social_user_id=social_user.id,
            social_type=social_user.type,
        )
        await self.social_user_bind_mapper.insert(social_user_bind)
        return social_user.openid

    @override
    @transactional
    async def unbind_social_user(
        self, user_id: int, user_type: int, social_type: int, openid: str
    ) -> None:
        if user_type == UserTypeEnum.ADMIN.code:
            await self.permission_service.require_user_writable(user_id)
        social_user = await self.social_user_mapper.select_by_type_and_openid(social_type, openid)
        if not social_user:
            raise ServiceException(ErrorCodeConstants.SOCIAL_USER_NOT_FOUND)
        await self.social_user_bind_mapper.delete_by_user_type_and_user_id_and_social_type(
            user_type, user_id, social_type
        )

    @override
    async def get_social_user_by_user_id(
        self, user_type: int, user_id: int, social_type: int
    ) -> SocialUserRespDTO | None:
        social_user_bind = (
            await self.social_user_bind_mapper.select_by_user_id_and_user_type_and_social_type(
                user_id, user_type, social_type
            )
        )
        if not social_user_bind:
            return None
        social_user = await self.social_user_mapper.select_by_id(social_user_bind.social_user_id)
        if not social_user:
            return None
        return SocialUserRespDTO(
            openid=social_user.openid,
            nickname=social_user.nickname,
            avatar=social_user.avatar,
            user_id=social_user_bind.user_id,
        )

    @override
    async def get_social_user_by_code(
        self, user_type: int, social_type: int, code: str, state: str
    ) -> SocialUserRespDTO | None:
        social_user = await self._auth_social_user(social_type, user_type, code, state)
        if not social_user:
            raise ServiceException(ErrorCodeConstants.SOCIAL_USER_NOT_FOUND)
        social_user_bind = (
            await self.social_user_bind_mapper.select_by_user_type_and_social_user_id(
                user_type, social_user.id
            )
        )
        return SocialUserRespDTO(
            openid=social_user.openid,
            nickname=social_user.nickname,
            avatar=social_user.avatar,
            user_id=social_user_bind.user_id if social_user_bind else None,
        )

    @override
    async def get_social_user_page(self, req: SocialUserPageReqVO) -> PageResult[SocialUserDO]:
        return await self.social_user_mapper.select_page(req)

    @override
    async def get_social_user(self, social_user_id: int) -> SocialUserDO | None:
        return await self.social_user_mapper.select_by_id(social_user_id)

    @transactional
    async def _auth_social_user(self, social_type, user_type, code, state):
        result = await self.social_client_service.get_auth_user(social_type, user_type, code, state)
        identity = result.identity
        statement = select(SocialUserDO).where(
            SocialUserDO.type == social_type,
            SocialUserDO.openid == identity.subject,
            SocialUserDO.client_id == identity.client_id,
            SocialUserDO.subject_type == identity.subject_type,
            SocialUserDO.application_id == identity.application_id,
        )
        existing = (await self.social_user_mapper.read(statement)).scalar_one_or_none()
        if existing is not None and user_type == UserTypeEnum.ADMIN.code:
            binding = await self.social_user_bind_mapper.select_by_user_type_and_social_user_id(
                user_type, existing.id
            )
            if binding is not None and await self.permission_service.has_any_roles(
                binding.user_id, RoleCodeEnum.READONLY.code
            ):
                # 授权码已验证，登录可以继续；演示账号的第三方资料和长期凭据保持原值。
                return existing
        values = dict(
            type=social_type,
            openid=identity.subject,
            client_id=identity.client_id,
            subject_type=identity.subject_type,
            application_id=identity.application_id,
            token=None
            if result.tokens.access_token is None
            else result.tokens.access_token.get_secret_value(),
            raw_token_info=result.tokens.to_storage_json().get_secret_value(),
            nickname=identity.nickname or identity.username or identity.subject,
            avatar=identity.avatar,
            raw_user_info=JsonUtils.to_json(identity.raw),
            code=code,
            state=state,
        )
        if existing is None:
            return await self.social_user_mapper.insert(SocialUserDO(**values))
        await self.social_user_mapper.update_by_id(SocialUserDO(id=existing.id, **values))
        return await self.social_user_mapper.select_by_id(existing.id)
