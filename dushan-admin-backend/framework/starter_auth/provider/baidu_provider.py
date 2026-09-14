from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class BaiduProvider(OAuthProvider):
    subject_field = "openid"
    capabilities = (ProviderCapability("BAIDU", refresh=True, revoke=True),)
    authorization_endpoint = "https://openapi.baidu.com/oauth/2.0/authorize"
    token_endpoint = "https://openapi.baidu.com/oauth/2.0/token"
    userinfo_endpoint = "https://openapi.baidu.com/rest/2.0/passport/users/getInfo"
    revoke_endpoint = "https://openapi.baidu.com/rest/2.0/passport/auth/revokeAuthorization"
    profile_fields = {"username": "username", "nickname": "username", "remark": "userdetail"}

    def authorization_parameters(self):
        return {**super().authorization_parameters(), "display": "popup"}

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET", self.userinfo_endpoint, params={"access_token": self.access(tokens)}
        )
        Payload.reject_errors(data)
        portrait = Payload.text(data, "portrait")
        return self.identity(
            data,
            Payload.identifier(data, "openid"),
            avatar=None
            if not portrait
            else "https://himg.bdimg.com/sys/portrait/item/" + portrait + ".jpg",
            gender={"1": "male", "2": "female"}.get(Payload.text(data, "sex")),
        )

    async def revoke(self, tokens):
        data = await self.http.json(
            "GET", self.revoke_endpoint, effect=True, params={"access_token": self.access(tokens)}
        )
        Payload.reject_errors(data)
        if Payload.integer(data, "result", required=True) != 1:
            raise AuthException(Codes.REJECTED, outcome="rejected")
