from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class SlackProvider(OAuthProvider):
    """Slack Sign in with Slack，使用官方 OpenID Connect 流程。

    官方资料：
    - Sign in with Slack: https://api.slack.com/authentication/sign-in-with-slack
    - Discovery: https://slack.com/.well-known/openid-configuration
    """

    subject_field = "sub"
    # openid.connect.token 的成功响应只有 ok/access_token/token_type/id_token，没有 expires_in。
    expires_required = False
    capabilities = (ProviderCapability("SLACK", oidc=True),)
    authorization_endpoint = "https://slack.com/openid/connect/authorize"
    token_endpoint = "https://slack.com/api/openid.connect.token"
    userinfo_endpoint = "https://slack.com/api/openid.connect.userInfo"
    fixed_scopes = ("openid", "profile", "email")
    oidc_metadata = OidcMetadata(
        issuer="https://slack.com",
        jwks_uri="https://slack.com/openid/connect/keys",
        algorithms=("RS256",),
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        discovery_uri="https://slack.com/.well-known/openid-configuration",
    )
    profile_fields = {
        "username": "name",
        "nickname": "name",
        "email": "email",
    }
