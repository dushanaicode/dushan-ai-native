from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class GithubProvider(OAuthProvider):
    expires_required = False
    capabilities = (ProviderCapability("GITHUB", pkce=True, refresh=True, refresh_rotation=True),)
    authorization_endpoint = "https://github.com/login/oauth/authorize"
    token_endpoint = "https://github.com/login/oauth/access_token"
    userinfo_endpoint = "https://api.github.com/user"
    profile_fields = {
        "username": "login",
        "nickname": "name",
        "avatar": "avatar_url",
        "blog": "blog",
        "company": "company",
        "location": "location",
        "email": "email",
        "remark": "bio",
    }
