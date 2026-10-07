from datetime import timezone
from typing import override

from pydantic import SecretStr, ValidationError

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.starter_auth.public import (
    AuthClientConfig,
    AuthClientProvider,
    AuthErrorCodes,
    AuthException,
)
from framework.starter_database.public import (
    DatabaseSettings,
)
from framework.starter_di.public import (
    Inject,
    conditional,
    service,
)
from framework.starter_security.public import (
    SecuritySettings,
)
from module_system.dal.mapper.social.social_client_mapper import SocialClientMapper
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.framework.social.model.social_auth_config import SocialAuthConfig


@service(interface=AuthClientProvider)
@conditional(lambda config: config.get_config(DatabaseSettings).enabled)
class SocialClientProviderAdapter(AuthClientProvider):
    mapper: SocialClientMapper = Inject()
    settings: SecuritySettings = Inject()

    @override
    async def get_client(self, application_id: str, source: str) -> AuthClientConfig | None:
        applications = {
            f"{self.settings.application_id}-admin": UserTypeEnum.ADMIN.code,
            f"{self.settings.application_id}-member": UserTypeEnum.MEMBER.code,
        }
        if application_id not in applications:
            return None
        types = {entry.auth_source: entry.code for entry in SocialTypeEnum}
        if source not in types:
            return None
        row = await self.mapper.select_by_social_type_and_user_type(
            types[source], applications[application_id]
        )
        if row is None:
            return None
        config = self._auth_config(row.auth_config)
        return AuthClientConfig(
            application_id=application_id,
            source=source,
            enabled=row.status == StatusEnum.ENABLE.code,
            revision=int(row.update_time.replace(tzinfo=timezone.utc).timestamp() * 1000000),
            client_id=row.client_id,
            client_secret=SecretStr(row.client_secret),
            redirect_uri=config.redirect_uri,
            scopes=config.scopes,
            pkce=config.pkce,
            options=config.options,
            credentials={name: SecretStr(value) for name, value in config.credentials.items()},
        )

    @staticmethod
    def _auth_config(value) -> SocialAuthConfig:
        """库里的认证配置是外部输入，结构不符按授权配置错误返回，不回显字段值。"""
        try:
            return SocialAuthConfig.model_validate(value)
        except ValidationError as error:
            raise AuthException(AuthErrorCodes.CONFIG, cause=error) from error
