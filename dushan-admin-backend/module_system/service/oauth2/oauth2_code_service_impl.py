from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from framework.common.exception import ServiceException
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    OpaqueToken,
)
from module_system.config.system_settings import SystemSettings
from module_system.dal.dataobject.oauth2.oauth2_code_do import OAuth2CodeDO
from module_system.dal.mapper.oauth2.oauth2_code_mapper import OAuth2CodeMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.oauth2.oauth2_code_service import OAuth2CodeService


@service(interface=OAuth2CodeService)
class OAuth2CodeServiceImpl(OAuth2CodeService):
    mapper: OAuth2CodeMapper = Inject()
    database: SessionProvider = Inject()
    settings: SystemSettings = Inject()

    @transactional
    async def create_authorization_code(
        self, user_id, user_type, client_id, scopes, redirect_uri, state
    ) -> str:
        code = OpaqueToken.generate()
        await self.mapper.insert(
            OAuth2CodeDO(
                code_digest=OpaqueToken.digest(code),
                user_id=user_id,
                user_type=user_type,
                client_id=client_id,
                scopes=list(scopes),
                redirect_uri=redirect_uri,
                state=state or "",
                expires_time=datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(seconds=self.settings.code_expire_seconds),
                consumed=False,
            )
        )
        return code

    @transactional
    async def consume_authorization_code(self, code, *, client_id, redirect_uri, state):
        async with self.database.transaction() as session:
            record = (
                await session.execute(
                    select(OAuth2CodeDO)
                    .where(OAuth2CodeDO.code_digest == OpaqueToken.digest(code))
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if record is None or record.consumed:
                raise ServiceException(ErrorCodeConstants.OAUTH2_CODE_NOT_EXISTS)
            if record.expires_time <= datetime.now(timezone.utc).replace(tzinfo=None):
                raise ServiceException(ErrorCodeConstants.OAUTH2_CODE_EXPIRE)
            if record.client_id != client_id:
                raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_CLIENT_ID_MISMATCH)
            if record.redirect_uri != redirect_uri:
                raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_REDIRECT_URI_MISMATCH)
            if record.state != (state or ""):
                raise ServiceException(ErrorCodeConstants.OAUTH2_GRANT_STATE_MISMATCH)
            await self.mapper.update_by_id(OAuth2CodeDO(id=record.id, consumed=True))
            return record
