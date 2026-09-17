from datetime import timezone

from pydantic import SecretStr

from framework.common.enums.status_enum import StatusEnum
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.spi.auth_client_provider import AuthClientProvider
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.config.security_settings import SecuritySettings
from module_system.dal.mapper.social.social_client_mapper import SocialClientMapper
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


@service(interface=AuthClientProvider)
@conditional(lambda config: config.get_config(DatabaseSettings).enabled)
class SocialClientProviderAdapter(AuthClientProvider):
    mapper: SocialClientMapper = Inject()
    settings: SecuritySettings = Inject()

    async def get_client(self, application_id: str, source: str):
        applications = {
            f"{self.settings.application_id}-admin": UserTypeEnum.ADMIN.code,
            f"{self.settings.application_id}-member": UserTypeEnum.MEMBER.code,
        }
        if application_id not in applications:
            return None
        types = {entry.label: entry.code for entry in SocialTypeEnum}
        types["WECHAT_ENTERPRISE_WEB"] = types.pop("WECHAT_ENTERPRISE_V2")
        if source not in types:
            return None
        row = await self.mapper.select_by_social_type_and_user_type(
            types[source], applications[application_id]
        )
        if row is None:
            return None
        config = row.auth_config
        return AuthClientConfig(
            application_id=application_id,
            source=source,
            enabled=row.status == StatusEnum.ENABLE.code,
            revision=int(row.update_time.replace(tzinfo=timezone.utc).timestamp() * 1000000),
            client_id=row.client_id,
            client_secret=SecretStr(row.client_secret),
            redirect_uri=config["redirect_uri"],
            scopes=tuple(config["scopes"]),
            pkce=config["pkce"],
            options=config["options"],
            credentials={name: SecretStr(value) for name, value in config["credentials"].items()},
        )
