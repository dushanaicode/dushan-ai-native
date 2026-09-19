from datetime import datetime, timezone

from framework.common.enums import UserTypeEnum
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.oauth2.dto.oauth2_session_dto import OAuth2SessionDTO
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.dal.mapper.dept.dept_mapper import DeptMapper
from module_system.dal.mapper.oauth2.oauth2_access_token_mapper import OAuth2AccessTokenMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper
from module_system.service.oauth2.oauth2_session_service import OAuth2SessionService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService


@service(interface=OAuth2SessionService)
class OAuth2SessionServiceImpl(OAuth2SessionService):
    tokens: OAuth2AccessTokenMapper = Inject()
    users: AdminUserMapper = Inject()
    departments: DeptMapper = Inject()
    sessions: OAuth2TokenService = Inject()

    async def list_sessions(self) -> list[OAuth2SessionDTO]:
        rows = await self.tokens.select_list(
            OAuth2AccessTokenDO.revoked.is_(False),
            OAuth2AccessTokenDO.user_type == UserTypeEnum.ADMIN.code,
            OAuth2AccessTokenDO.expires_time > datetime.now(timezone.utc).replace(tzinfo=None),
        )
        users = {
            user.id: user for user in await self.users.select_by_ids({row.user_id for row in rows})
        }
        departments = {
            entry.id: entry.name
            for entry in await self.departments.select_by_ids(
                {u.dept_id for u in users.values() if u.dept_id is not None}
            )
        }
        values = []
        for row in rows:
            if row.user_id not in users:
                continue
            session = await self.sessions.resolve_session(
                row.token_digest, application_id=row.application_id, domain=row.domain
            )
            if session is None:
                continue
            user = users[row.user_id]
            info = row.user_info or {}
            values.append(
                OAuth2SessionDTO(
                    family_id=row.family_id,
                    user_id=user.id,
                    username=user.username,
                    nickname=user.nickname,
                    dept_name=departments.get(user.dept_id),
                    ipaddr=info.get("ipaddr"),
                    login_location=info.get("login_location"),
                    browser=info.get("browser"),
                    os=info.get("os"),
                    login_time=row.create_time,
                )
            )
        return values

    async def revoke_session(self, family_id: str) -> None:
        rows = await self.tokens.select_list(OAuth2AccessTokenDO.family_id == family_id)
        await self.sessions.remove_access_token_batch([row.id for row in rows])
