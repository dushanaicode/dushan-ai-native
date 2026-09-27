from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider


class GithubProvider(OAuthProvider):
    """GitHub OAuth App 网页授权。

    官方资料：
    - 授权: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
    - 创建应用: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app
    - 用户接口: https://docs.github.com/en/rest/users/users#get-the-authenticated-user
    实现端点：
    - authorization: https://github.com/login/oauth/authorize
    - token: https://github.com/login/oauth/access_token
    - userinfo: https://api.github.com/user
    """

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
