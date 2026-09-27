from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class MeituanProvider(OAuthProvider):
    """美团外卖开放平台 OAuth 授权。

    官方资料：
    - 开放平台: https://openapi.meituan.com/
    - 服务端文档: https://docs.meituan.com/
    实现端点：
    - authorization: https://openapi.waimai.meituan.com/oauth/authorize
    - token: https://openapi.waimai.meituan.com/oauth/access_token
    - refresh: https://openapi.waimai.meituan.com/oauth/refresh_token
    - userinfo: https://openapi.waimai.meituan.com/oauth/userinfo
    """

    subject_field = "openid"
    capabilities = (ProviderCapability("MEITUAN", refresh=True),)
    authorization_endpoint = "https://openapi.waimai.meituan.com/oauth/authorize"
    token_endpoint = "https://openapi.waimai.meituan.com/oauth/access_token"
    userinfo_endpoint = "https://openapi.waimai.meituan.com/oauth/userinfo"
    refresh_endpoint = "https://openapi.waimai.meituan.com/oauth/refresh_token"
    fixed_scopes = ()
    profile_fields = {"username": "nickname", "nickname": "nickname", "avatar": "avatar"}

    def client_fields(self):
        return {
            "app_id": self.config.client_id,
            "secret": self.config.client_secret.get_secret_value(),
        }

    async def userinfo(self, tokens):
        data = await self.http.json(
            "POST",
            self.userinfo_endpoint,
            data={**self.client_fields(), "access_token": self.access(tokens)},
        )
        Payload.reject_errors(data)
        return self.identity(data, Payload.text(data, "openid", required=True))
