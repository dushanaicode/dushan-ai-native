from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class GiteeProvider(OAuthProvider):
    """Gitee OAuth 2.0 授权。

    官方资料：
    - OAuth: https://gitee.com/api/v5/oauth_doc#/
    - API: https://gitee.com/api/v5/swagger
    实现端点：
    - authorization: https://gitee.com/oauth/authorize
    - token: https://gitee.com/oauth/token
    - userinfo: https://gitee.com/api/v5/user
    """

    capabilities = (ProviderCapability("GITEE"),)
    authorization_endpoint = "https://gitee.com/oauth/authorize"
    token_endpoint = "https://gitee.com/oauth/token"
    userinfo_endpoint = "https://gitee.com/api/v5/user"
    profile_fields = {
        "username": "login",
        "nickname": "name",
        "avatar": "avatar_url",
        "blog": "blog",
        "company": "company",
        "location": "address",
        "email": "email",
        "remark": "bio",
    }

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET", self.userinfo_endpoint, params={"access_token": self.access(tokens)}
        )
        Payload.reject_errors(data)
        return self.identity(data, Payload.identifier(data, "id"))
