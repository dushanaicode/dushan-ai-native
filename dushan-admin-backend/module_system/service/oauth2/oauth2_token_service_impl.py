from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.starter_cache.public import CacheHandler
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    LoginSession,
    OpaqueToken,
    SecurityErrorCodes,
    SecurityException,
    SecurityRealm,
    SecuritySettings,
    TenantAccessMode,
)
from framework.starter_tenant.public import (
    TenantContext,
    TenantSettings,
)
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.cache.oauth2.oauth2_access_token_redis_dao import OAuth2AccessTokenRedisDAO
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.dal.dataobject.oauth2.oauth2_refresh_token_do import OAuth2RefreshTokenDO
from module_system.dal.mapper.auth.system_authentication_mapper import SystemAuthenticationMapper
from module_system.dal.mapper.oauth2.oauth2_access_token_mapper import OAuth2AccessTokenMapper
from module_system.dal.mapper.oauth2.oauth2_refresh_token_mapper import OAuth2RefreshTokenMapper
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=OAuth2TokenService)
class OAuth2TokenServiceImpl(OAuth2TokenService):
    workloads: SystemWorkloadService = Inject()
    tenant_settings: TenantSettings = Inject()
    ticket_cache: CacheHandler = Inject()
    database: SessionProvider = Inject()
    settings: SecuritySettings = Inject()
    tenant: TenantContext = Inject()
    authentication: SystemAuthenticationMapper = Inject()
    clients: OAuth2ClientService = Inject()
    access_tokens: OAuth2AccessTokenMapper = Inject()
    refresh_tokens: OAuth2RefreshTokenMapper = Inject()
    cache: OAuth2AccessTokenRedisDAO = Inject()

    async def _subject(self, user_id, user_type, client):
        if client.user_type is not None and client.user_type != user_type:
            raise SecurityException(SecurityErrorCodes.INVALID)
        if user_type == UserTypeEnum.ADMIN.code:
            user = await self.authentication.user_by_id(
                user_id, self.tenant.get_required_tenant_id()
            )
            if user is None or user.status != StatusEnum.ENABLE.code:
                raise SecurityException(SecurityErrorCodes.DISABLED)
            return user.credential_revision, {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "dept_id": user.dept_id,
            }
        if user_type == UserTypeEnum.CLIENT.code and user_id == client.id:
            return client.credential_revision, {}
        raise SecurityException(SecurityErrorCodes.INVALID)

    @transactional
    async def create_access_token(
        self, user_id: int, user_type: int, client_id: str, scopes: list[str]
    ) -> OAuth2AccessTokenRespDTO:
        client = await self.clients.validate_client(client_id, scopes=scopes)
        revision, info = await self._subject(user_id, user_type, client)
        return await self._issue(user_id, user_type, client, scopes, revision, info, uuid4().hex)

    async def _issue(
        self, user_id, user_type, client, scopes, revision, info, family_id, *, refresh_expires=None
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        access_secret, refresh_secret = OpaqueToken.generate(), OpaqueToken.generate()
        refresh = OAuth2RefreshTokenDO(
            token_digest=OpaqueToken.digest(refresh_secret),
            user_id=user_id,
            user_type=user_type,
            client_id=client.client_id,
            scopes=list(scopes),
            family_id=family_id,
            credential_revision=revision,
            revoked=False,
            consumed_time=None,
            expires_time=now + timedelta(seconds=client.refresh_token_validity_seconds)
            if refresh_expires is None
            else refresh_expires,
            application_id=self.settings.application_id,
            domain=self.settings.default_domain,
        )
        await self.refresh_tokens.insert(refresh)
        access = OAuth2AccessTokenDO(
            token_digest=OpaqueToken.digest(access_secret),
            refresh_token_id=refresh.id,
            user_id=user_id,
            user_type=user_type,
            user_info=info,
            client_id=client.client_id,
            scopes=list(scopes),
            family_id=family_id,
            credential_revision=revision,
            revoked=False,
            expires_time=now + timedelta(seconds=client.access_token_validity_seconds),
            application_id=self.settings.application_id,
            domain=self.settings.default_domain,
        )
        await self.access_tokens.insert(access)
        self.database.after_commit(
            lambda: self.cache.cache_token(access), required=True, name="oauth2-cache"
        )
        return OAuth2AccessTokenRespDTO(
            access_token=access_secret,
            refresh_token=refresh_secret,
            user_id=user_id,
            user_type=user_type,
            tenant_id=self.tenant.get_required_tenant_id(),
            client_id=client.client_id,
            scopes=list(scopes),
            expires_time=access.expires_time,
            refresh_expires_time=refresh.expires_time,
        )

    async def refresh_access_token(
        self, refresh_token: str, client_id: str
    ) -> OAuth2AccessTokenRespDTO:
        digest = OpaqueToken.digest(refresh_token)
        client = await self.clients.validate_client(client_id, grant_type="refresh_token")
        failure = None
        issued = None
        # 重放撤销必须先提交，再报告失败，不能随外层异常回滚。
        async with self.database.transaction(propagation="requires_new") as session:
            row = (
                await session.execute(
                    select(OAuth2RefreshTokenDO)
                    .where(
                        OAuth2RefreshTokenDO.token_digest == digest,
                        OAuth2RefreshTokenDO.application_id == self.settings.application_id,
                        OAuth2RefreshTokenDO.domain == self.settings.default_domain,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if row is None or row.client_id != client_id:
                failure = SecurityException(SecurityErrorCodes.INVALID)
            elif row.revoked or row.consumed_time is not None:
                await self._revoke_family(row.family_id)
                failure = SecurityException(SecurityErrorCodes.REVOKED)
            elif row.expires_time <= datetime.now(timezone.utc).replace(tzinfo=None):
                failure = SecurityException(SecurityErrorCodes.EXPIRED)
            else:
                revision, info = await self._subject(row.user_id, row.user_type, client)
                if revision != row.credential_revision:
                    await self._revoke_family(row.family_id)
                    failure = SecurityException(SecurityErrorCodes.CREDENTIALS)
                else:
                    await self.refresh_tokens.update_by_id(
                        OAuth2RefreshTokenDO(
                            id=row.id, consumed_time=datetime.now(timezone.utc).replace(tzinfo=None)
                        )
                    )
                    await self.access_tokens.update_by_condition(
                        {"revoked": True}, OAuth2AccessTokenDO.family_id == row.family_id
                    )
                    issued = await self._issue(
                        row.user_id,
                        row.user_type,
                        client,
                        row.scopes or [],
                        revision,
                        info,
                        row.family_id,
                        refresh_expires=row.expires_time,
                    )
        if failure is not None:
            raise failure
        return issued

    async def resolve_session(
        self, token_digest: str, *, application_id: str, domain: str
    ) -> LoginSession | None:
        if application_id != self.settings.application_id or domain not in self.settings.domains:
            return None
        facts = await self.authentication.session_facts(token_digest, application_id, domain)
        if facts is None:
            return None
        admin = facts["user_type"] == UserTypeEnum.ADMIN.code
        client = facts["user_type"] == UserTypeEnum.CLIENT.code
        if not admin and not client or admin and facts["current_user_credential_revision"] is None:
            return None
        tenant_id = facts["tenant_id"] if admin else None
        account_id = str(facts["user_id"]) if admin else f"client:{facts['user_id']}"
        enabled = facts["client_status"] == StatusEnum.ENABLE.code and (
            facts["account_status"] == StatusEnum.ENABLE.code
            if admin
            else facts["client_record_id"] == facts["user_id"]
            and facts["client_user_type"] == UserTypeEnum.CLIENT.code
        )
        current_revision = (
            facts["current_user_credential_revision"]
            if admin
            else facts["current_client_credential_revision"]
        )
        return LoginSession(
            application_id=application_id,
            domain=domain,
            token_digest=token_digest,
            session_id=str(facts["id"]),
            family_id=facts["family_id"],
            account_id=account_id,
            realm=SecurityRealm.TENANT if admin else SecurityRealm.ACCOUNT,
            expires_at=facts["expires_time"].replace(tzinfo=timezone.utc),
            revoked=facts["revoked"],
            account_enabled=enabled,
            credential_revision=facts["credential_revision"],
            current_credential_revision=current_revision,
            authorization_revision=f"{facts['global_revision']}:{facts['user_authorization_revision'] if admin else current_revision}",
            scopes=frozenset(facts["scopes"] or []),
            tenant_id=tenant_id,
            membership_id=account_id if admin else None,
            authority_tenant_id=tenant_id,
            authority_membership_id=account_id if admin else None,
            dept_id=str(facts["account_dept_id"])
            if admin and facts["account_dept_id"] is not None
            else None,
            access_mode=TenantAccessMode.DIRECT_MEMBERSHIP if admin else None,
        )

    async def _validated(self, token: str):
        identity = await self.resolve_session(
            OpaqueToken.digest(token),
            application_id=self.settings.application_id,
            domain=self.settings.default_domain,
        )
        if identity is None:
            raise SecurityException(SecurityErrorCodes.INVALID)
        if identity.revoked:
            raise SecurityException(SecurityErrorCodes.REVOKED)
        if not identity.account_enabled:
            raise SecurityException(SecurityErrorCodes.DISABLED)
        if identity.expires_at <= datetime.now(timezone.utc):
            raise SecurityException(SecurityErrorCodes.EXPIRED)
        if identity.credential_revision != identity.current_credential_revision:
            raise SecurityException(SecurityErrorCodes.CREDENTIALS)
        return identity

    async def check_access_token(self, access_token: str) -> OAuth2AccessTokenDO:
        identity = await self._validated(access_token)
        facts = await self.authentication.session_facts(
            identity.token_digest, identity.application_id, identity.domain
        )
        if facts is None or facts["revoked"]:
            raise SecurityException(SecurityErrorCodes.REVOKED)
        return OAuth2AccessTokenDO(
            **{column.key: facts[column.key] for column in OAuth2AccessTokenDO.__table__.c}
        )

    async def get_access_token(self, access_token: str) -> OAuth2AccessTokenDO | None:
        try:
            return await self.check_access_token(access_token)
        except SecurityException as error:
            if error.is_authentication_error:
                return None
            raise

    @transactional
    async def _revoke_family(self, family_id: str):
        rows = await self.access_tokens.select_list(OAuth2AccessTokenDO.family_id == family_id)
        await self.access_tokens.update_by_condition(
            {"revoked": True}, OAuth2AccessTokenDO.family_id == family_id
        )
        await self.refresh_tokens.revoke_family(family_id)
        identifiers = [self.cache.identifier(row.tenant_id, row.token_digest) for row in rows]
        self.database.after_commit(
            lambda: self.cache.delete_many(identifiers), required=True, name="oauth2-revoke"
        )

    async def revoke_session(self, session: LoginSession):
        async with self.workloads.scope("system.auth", self.tenant_settings.default_tenant_id):
            await self._revoke_family(session.family_id)

    @transactional
    async def remove_access_token(self, access_token: str):
        token = await self.access_tokens.select_by_digest(OpaqueToken.digest(access_token))
        if token is not None:
            await self._revoke_family(token.family_id)
        return token

    @transactional
    async def remove_access_token_batch(self, ids: list[int]) -> int:
        tokens = await self.access_tokens.select_by_ids(ids)
        for family_id in {token.family_id for token in tokens}:
            await self._revoke_family(family_id)
        return len(tokens)

    async def get_access_token_page(self, req_vo):
        return await self.access_tokens.select_page(req_vo)

    async def get_access_tokens_by_user_id(self, user_id: int, user_type: int):
        return await self.access_tokens.select_list_by_user_id(user_id, user_type)

    async def verify_token_and_get_user(
        self, token: str, user_type: int | None = None
    ) -> LoginSession:
        identity = await self._validated(token)
        expected = (
            UserTypeEnum.CLIENT.code
            if identity.realm is SecurityRealm.ACCOUNT
            else UserTypeEnum.ADMIN.code
        )
        if user_type is not None and user_type != expected:
            raise SecurityException(SecurityErrorCodes.INVALID)
        return identity

    async def build_user_info(self, user_id: int, user_type: int) -> dict:
        if user_type != UserTypeEnum.ADMIN.code:
            return {}
        user = await self.authentication.user_by_id(user_id, self.tenant.get_required_tenant_id())
        if user is None:
            raise SecurityException(SecurityErrorCodes.INVALID)
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "dept_id": user.dept_id,
        }

    async def create_socket_ticket(self, identity: LoginSession) -> str:
        ticket = OpaqueToken.generate()
        await self.ticket_cache.set(
            SystemCacheKeys.WEBSOCKET_TICKET,
            OpaqueToken.digest(ticket),
            {
                "digest": identity.token_digest,
                "application_id": identity.application_id,
                "domain": identity.domain,
            },
        )
        return ticket

    async def consume_socket_ticket(
        self, ticket: str, *, application_id: str, domain: str
    ) -> LoginSession:
        result = await self.ticket_cache.get_and_delete(
            SystemCacheKeys.WEBSOCKET_TICKET, OpaqueToken.digest(ticket)
        )
        if (
            not result.hit
            or result.value["application_id"] != application_id
            or result.value["domain"] != domain
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        session = await self.resolve_session(
            result.value["digest"], application_id=application_id, domain=domain
        )
        if session is None:
            raise SecurityException(SecurityErrorCodes.INVALID)
        return session
