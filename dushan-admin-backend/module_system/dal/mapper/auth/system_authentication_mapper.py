from __future__ import annotations

from sqlalchemy import and_, select

from framework.common.enums.user_type_enum import UserTypeEnum
from framework.starter_database.query.authentication_reader import AuthenticationReader
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import repository
from framework.starter_tenant.config.tenant_settings import TenantSettings
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO
from module_system.dal.dataobject.permission.authorization_revision_do import (
    AuthorizationRevisionDO,
)
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO


@repository
class SystemAuthenticationMapper:
    """认证所需的有限主库投影；普通用户 CRUD 仍使用受保护 AdminUserMapper。"""

    def __init__(self, database: SessionProvider, tenant: TenantSettings):
        self.database, self.tenant = (database, tenant)

    def _reader(self, tenant_id: str):
        return AuthenticationReader(
            self.database,
            (AdminUserDO, OAuth2AccessTokenDO, OAuth2ClientDO, AuthorizationRevisionDO),
            tenant_id=tenant_id,
        )

    async def user_by_username(self, username: str):
        return await self._user(AdminUserDO.__table__.c.username == username)

    async def user_by_mobile(self, mobile: str):
        return await self._user(AdminUserDO.__table__.c.mobile == mobile)

    async def user_by_id(self, user_id: int, tenant_id: str | None = None):
        return await self._user(AdminUserDO.__table__.c.id == user_id, tenant_id=tenant_id)

    async def _user(self, condition, *, tenant_id: str | None = None):
        rows = await self._reader(
            self.tenant.default_tenant_id if tenant_id is None else tenant_id
        ).read(select(AdminUserDO.__table__).where(condition))
        if len(rows) > 1:
            raise ValueError("认证标识不唯一")
        return None if not rows else AdminUserDO(**rows[0])

    async def session_facts(self, digest: str, application_id: str, domain: str):
        access, user, client, revision = (
            OAuth2AccessTokenDO.__table__,
            AdminUserDO.__table__,
            OAuth2ClientDO.__table__,
            AuthorizationRevisionDO.__table__,
        )
        statement = (
            select(
                *access.c,
                user.c.status.label("account_status"),
                user.c.credential_revision.label("current_user_credential_revision"),
                user.c.authorization_revision.label("user_authorization_revision"),
                user.c.dept_id.label("account_dept_id"),
                client.c.id.label("client_record_id"),
                client.c.status.label("client_status"),
                client.c.user_type.label("client_user_type"),
                client.c.credential_revision.label("current_client_credential_revision"),
                select(revision.c.revision)
                .where(revision.c.id == 1)
                .scalar_subquery()
                .label("global_revision"),
            )
            .select_from(access)
            .outerjoin(
                user,
                and_(
                    access.c.user_type == UserTypeEnum.ADMIN.code,
                    access.c.user_id == user.c.id,
                    access.c.tenant_id == user.c.tenant_id,
                ),
            )
            .join(client, access.c.client_id == client.c.client_id)
            .where(
                access.c.token_digest == digest,
                access.c.application_id == application_id,
                access.c.domain == domain,
            )
        )
        rows = await self._reader(self.tenant.default_tenant_id).read(statement)
        return None if not rows else rows[0]

    async def authorization_revision(self, user_id: int, tenant_id: str):
        rows = await self._reader(tenant_id).read(
            select(
                AdminUserDO.__table__.c.authorization_revision.label("user_revision"),
                select(AuthorizationRevisionDO.__table__.c.revision)
                .where(AuthorizationRevisionDO.__table__.c.id == 1)
                .scalar_subquery()
                .label("global_revision"),
            )
            .select_from(AdminUserDO.__table__)
            .where(AdminUserDO.__table__.c.id == user_id)
        )
        if not rows:
            raise ValueError("授权主体或权限版本不存在")
        row = rows[0]
        return f"{row['global_revision']}:{row['user_revision']}"

    async def department_members(self, tenant_id: str, department_ids: set[int]):
        rows = await self._reader(tenant_id).read(
            select(AdminUserDO.__table__.c.id).where(
                AdminUserDO.__table__.c.dept_id.in_(department_ids)
            )
        )
        return frozenset((str(row["id"]) for row in rows))
