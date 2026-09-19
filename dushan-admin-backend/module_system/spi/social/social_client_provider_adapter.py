from datetime import timezone

from pydantic import SecretStr

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.starter_auth.public import (
    AuthClientConfig,
    AuthClientProvider,
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
