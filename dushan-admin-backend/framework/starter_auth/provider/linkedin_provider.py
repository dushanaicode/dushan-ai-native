from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class LinkedinProvider(OAuthProvider):
    """LinkedIn Sign In using OpenID Connect。

    官方资料：
    - OIDC: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2
    - OAuth: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication
    - Discovery: https://www.linkedin.com/oauth/.well-known/openid-configuration
    """

    subject_field = "sub"
    capabilities = (ProviderCapability("LINKEDIN", oidc=True),)
    authorization_endpoint = "https://www.linkedin.com/oauth/v2/authorization"
    token_endpoint = "https://www.linkedin.com/oauth/v2/accessToken"
    userinfo_endpoint = "https://api.linkedin.com/v2/userinfo"
    fixed_scopes = ("openid", "profile", "email")
    oidc_metadata = OidcMetadata(
        issuer="https://www.linkedin.com/oauth",
        jwks_uri="https://www.linkedin.com/oauth/openid/jwks",
        algorithms=("RS256",),
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        discovery_uri="https://www.linkedin.com/oauth/.well-known/openid-configuration",
        # LinkedIn 的 discovery 声明 issuer 为 .../oauth，实际签发的 ID Token 报告过
        # https://www.linkedin.com；两个取值都属 LinkedIn 固定域名，按白名单接受其一。
        issuer_pattern=r"https://www\.linkedin\.com(?:/oauth)?",
        # 授权请求不接受 nonce，ID Token 载荷也只有 iss/sub/aud/iat/exp，
        # 重放由一次性授权码、state 绑定和后端直连令牌端点共同约束。
        nonce_supported=False,
    )
    profile_fields = {
        "username": "email",
        "nickname": "name",
        "avatar": "picture",
        "email": "email",
    }
