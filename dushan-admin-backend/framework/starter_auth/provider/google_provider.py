from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class GoogleProvider(OAuthProvider):
    """Google OAuth 2.0 / OpenID Connect 登录。

    官方资料：
    - OAuth 网页服务: https://developers.google.com/identity/protocols/oauth2/web-server
    - Discovery: https://accounts.google.com/.well-known/openid-configuration
    """

    subject_field = "sub"
    capabilities = (ProviderCapability("GOOGLE", oidc=True, pkce=True, refresh=True),)
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
    fixed_scopes = ("openid", "profile", "email")
    oidc_metadata = OidcMetadata(
        issuer="https://accounts.google.com",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        algorithms=("RS256",),
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        discovery_uri="https://accounts.google.com/.well-known/openid-configuration",
    )
    profile_fields = {
        "username": "email",
        "nickname": "name",
        "avatar": "picture",
        "email": "email",
    }

    def authorization_parameters(self):
        # refresh_token 只在 access_type=offline 时签发，且仅在用户首次同意时返回一次。
        return {**super().authorization_parameters(), "access_type": "offline"}
