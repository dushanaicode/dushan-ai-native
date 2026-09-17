from __future__ import annotations

from typing import override

from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService
from module_system.service.oauth2.oauth2_code_service import OAuth2CodeService
from module_system.service.oauth2.oauth2_grant_service import OAuth2GrantService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=OAuth2GrantService)
class OAuth2GrantServiceImpl(OAuth2GrantService):
    """OAuth2 授权服务实现类"""

    oauth2_token_service: OAuth2TokenService = Inject()
    oauth2_code_service: OAuth2CodeService = Inject()
    oauth2_admin_auth_service: AuthAdminAuthService = Inject()
    oauth2_client_service: OAuth2ClientService = Inject()

    @override
    async def grant_implicit(
        self, user_id: int, user_type: int, client_id: str, scopes: list
    ) -> OAuth2AccessTokenRespDTO:
        return await self.oauth2_token_service.create_access_token(
            user_id, user_type, client_id, scopes
        )

    @override
    async def grant_authorization_code_for_code(
        self,
        user_id: int,
        user_type: int,
        client_id: str,
        scopes: list,
        redirect_uri: str,
        state: str,
    ) -> str:
        code_do = await self.oauth2_code_service.create_authorization_code(
            user_id, user_type, client_id, scopes, redirect_uri, state
        )
        return code_do

    @override
    @transactional
    async def grant_authorization_code_for_access_token(
        self, client_id: str, code: str, redirect_uri: str, state: str
    ) -> OAuth2AccessTokenRespDTO:
        code_do = await self.oauth2_code_service.consume_authorization_code(
            code, client_id=client_id, redirect_uri=redirect_uri, state=state
        )
        if not code_do:
            raise ServiceException(ErrorCodeConstants.OAUTH2_CODE_NOT_EXISTS)
        client = await self.oauth2_client_service.validate_client(client_id)
        if client.user_type is not None and client.user_type != code_do.user_type:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_CLIENT_USER_TYPE_MISMATCH)
        if client_id != code_do.client_id:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_CLIENT_ID_MISMATCH)
        if redirect_uri != code_do.redirect_uri:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_REDIRECT_URI_MISMATCH)
        if (state or "") != code_do.state:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_STATE_MISMATCH)
        return await self.oauth2_token_service.create_access_token(
            code_do.user_id, code_do.user_type, code_do.client_id, code_do.scopes
        )

    @override
    async def grant_password(
        self, username: str, password: str, client_id: str, scopes: list, user_type: int
    ) -> OAuth2AccessTokenRespDTO:
        user: AdminUserDO = await self.oauth2_admin_auth_service.authenticate(username, password)
        if not user:
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_BAD_CREDENTIALS)
        client = await self.oauth2_client_service.validate_client(client_id)
        if client.user_type is not None and client.user_type != user_type:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_CLIENT_USER_TYPE_MISMATCH)
        return await self.oauth2_token_service.create_access_token(
            user.id, UserTypeEnum.ADMIN.code, client_id, scopes
        )

    @override
    async def grant_refresh_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO:
        return await self.oauth2_token_service.refresh_access_token(refresh_token, client_id)

    @override
    async def grant_client_credentials(
        self, client_id: str, scopes: list
    ) -> OAuth2AccessTokenRespDTO:
        client: OAuth2ClientDTO = await self.oauth2_client_service.validate_client(client_id)
        if client.user_type != UserTypeEnum.CLIENT.code:
            raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_CLIENT_NOT_CLIENT_TYPE)
        return await self.oauth2_token_service.create_access_token(
            user_id=client.id,
            user_type=UserTypeEnum.CLIENT.code,
            client_id=client_id,
            scopes=scopes,
        )

    @override
    async def revoke_token(self, client_id: str, access_token: str) -> bool:
        access_token_do = await self.oauth2_token_service.get_access_token(access_token)
        if not access_token_do or access_token_do.client_id != client_id:
            return False
        removed = await self.oauth2_token_service.remove_access_token(access_token)
        return removed is not None
