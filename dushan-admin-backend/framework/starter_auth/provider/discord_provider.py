from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class DiscordProvider(OAuthProvider):
    """Discord OAuth 2.0 用户登录。

    官方文档：
    - OAuth: https://discord.com/developers/docs/topics/oauth2
    实现端点：
    - authorization: https://discord.com/oauth2/authorize
    - token: https://discord.com/api/oauth2/token
    - userinfo: https://discord.com/api/users/@me
    """

    subject_field = "id"
    capabilities = (ProviderCapability("DISCORD", refresh=True),)
    authorization_endpoint = "https://discord.com/oauth2/authorize"
    token_endpoint = "https://discord.com/api/oauth2/token"
    userinfo_endpoint = "https://discord.com/api/users/@me"
    fixed_scopes = ("identify", "email")
    profile_fields = {
        "username": "username",
        "nickname": "global_name",
        "email": "email",
    }

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"Authorization": "Bearer " + self.access(tokens)},
        )
        Payload.reject_errors(data)
        subject = Payload.identifier(data, "id")
        # 用户对象里的 avatar 是头像散列而不是地址，按官方 CDN 规则拼出可访问的 URL。
        avatar = Payload.text(data, "avatar")
        return self.identity(
            data,
            subject,
            avatar=None
            if avatar is None
            else f"https://cdn.discordapp.com/avatars/{subject}/{avatar}.png",
        )
