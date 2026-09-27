import re

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class MicrosoftProvider(OAuthProvider):
    """Microsoft Entra ID OAuth 2.0 / OIDC 多租户登录。

    官方资料：
    - 授权码: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
    - 多租户 Discovery: https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration

    `options.tenant` 缺省为 common；单租户填租户 GUID。要拿到 refresh_token 需要在
    scopes 中申请 offline_access。
    """

    subject_field = "sub"
    capabilities = (ProviderCapability("MICROSOFT", oidc=True, pkce=True, refresh=True),)
    allowed_options = frozenset(("tenant",))
    userinfo_endpoint = "https://graph.microsoft.com/oidc/userinfo"
    profile_fields = {
        "username": "preferred_username",
        "nickname": "name",
        "email": "email",
    }
    _TENANT_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    _SHARED_TENANTS = frozenset(("common", "organizations", "consumers"))
    # 多租户场景下 issuer 带的是实际租户 GUID，common 的 discovery 则返回 {tenantid} 占位。
    _issuer_pattern = (
        r"https://login\.microsoftonline\.com/(?:" + _TENANT_GUID + r"|\{tenantid\})/v2\.0"
    )
    oidc_metadata = OidcMetadata(
        issuer="https://login.microsoftonline.com/common/v2.0",
        jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys",
        algorithms=("RS256",),
        authorization_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        discovery_uri="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        issuer_pattern=_issuer_pattern,
    )

    @classmethod
    def _tenant(cls, value: str | None) -> str:
        """租户只接受 common/organizations/consumers 或租户 GUID。

        Entra ID 即使按域名请求，discovery 与 ID Token 的 issuer 仍然是 GUID 形式，
        按域名配置会让 issuer 比对必然失败，因此在配置阶段就要求填写 GUID。
        """
        tenant = "common" if value is None else value
        if tenant not in cls._SHARED_TENANTS and re.fullmatch(cls._TENANT_GUID, tenant) is None:
            raise AuthException(Codes.CONFIG)
        return tenant

    @property
    def authorization_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self._tenant(self.config.options.get('tenant'))}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self._tenant(self.config.options.get('tenant'))}/oauth2/v2.0/token"

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        cls._tenant(config.options.get("tenant"))

    def oidc_metadata_for_config(self) -> OidcMetadata:
        tenant = self._tenant(self.config.options.get("tenant"))
        if tenant in self._SHARED_TENANTS:
            return self.oidc_metadata
        base = f"https://login.microsoftonline.com/{tenant}"
        return OidcMetadata(
            issuer=f"{base}/v2.0",
            jwks_uri=f"{base}/discovery/v2.0/keys",
            algorithms=("RS256",),
            authorization_endpoint=f"{base}/oauth2/v2.0/authorize",
            token_endpoint=f"{base}/oauth2/v2.0/token",
            discovery_uri=f"{base}/v2.0/.well-known/openid-configuration",
        )
