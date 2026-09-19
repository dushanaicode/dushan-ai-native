from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class WeiboProvider(OAuthProvider):
    subject_field = "idstr"
    capabilities = (ProviderCapability("WEIBO", revoke=True),)
    authorization_endpoint = "https://api.weibo.com/oauth2/authorize"
    token_endpoint = "https://api.weibo.com/oauth2/access_token"
    userinfo_endpoint = "https://api.weibo.com/2/users/show.json"
    revoke_endpoint = "https://api.weibo.com/oauth2/revokeoauth2"
    scope_separator = ","
    profile_fields = {
        "username": "name",
        "nickname": "screen_name",
        "avatar": "profile_image_url",
        "location": "location",
        "remark": "description",
    }

    def token(self, data, **values):
        Payload.reject_errors(data)
        return super().token(data, subject=Payload.identifier(data, "uid"), **values)

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            params={"access_token": self.access(tokens), "uid": tokens.subject},
        )
        Payload.reject_errors(data)
        subject = Payload.identifier(data, "idstr")
        if subject != tokens.subject:
            raise AuthException(Codes.BINDING)
        return self.identity(
            data,
            subject,
            blog=Payload.text(data, "url"),
            gender={"m": "male", "f": "female"}.get(Payload.text(data, "gender")),
        )

    async def revoke(self, tokens):
        data = await self.http.json(
            "POST", self.revoke_endpoint, effect=True, data={"access_token": self.access(tokens)}
        )
        Payload.reject_errors(data)
        if Payload.text(data, "result", required=True) != "true":
            raise AuthException(Codes.REJECTED, outcome="rejected")
