from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class DouyinProvider(OAuthProvider):
    subject_field = "open_id"
    capabilities = (ProviderCapability("DOUYIN", refresh=True),)
    authorization_endpoint = "https://open.douyin.com/platform/oauth/connect"
    token_endpoint = "https://open.douyin.com/oauth/access_token/"
    userinfo_endpoint = "https://open.douyin.com/oauth/userinfo/"
    refresh_endpoint = "https://open.douyin.com/oauth/refresh_token/"
    client_parameter = "client_key"
    scope_separator = ","
    profile_fields = {
        "username": "nickname",
        "nickname": "nickname",
        "avatar": "avatar",
        "remark": "description",
    }

    def client_fields(self):
        return {
            "client_key": self.config.client_id,
            "client_secret": self.config.client_secret.get_secret_value(),
        }

    def token(self, data, **values):
        Payload.reject_errors(data)
        payload = Payload.object(data, "data")
        Payload.reject_errors(payload)
        return super().token(
            payload,
            subject=Payload.text(payload, "open_id", required=True),
            refresh_expires_in=Payload.integer(payload, "refresh_expires_in"),
            **values,
        )

    async def refresh(self, tokens):
        data = await self.http.json(
            "POST",
            self.refresh_endpoint,
            effect=True,
            data={
                "client_key": self.config.client_id,
                "refresh_token": self.refresh_value(tokens),
                "grant_type": "refresh_token",
            },
        )
        refreshed = self.token(data)
        return refreshed

    async def userinfo(self, tokens):
        result = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            params={"access_token": self.access(tokens), "open_id": tokens.subject},
        )
        Payload.reject_errors(result)
        data = Payload.object(result, "data")
        Payload.reject_errors(data)
        subject = Payload.text(data, "open_id", required=True)
        if subject != tokens.subject:
            raise AuthException(Codes.BINDING)
        return self.identity(
            data,
            subject,
            union_id=Payload.text(data, "union_id"),
            gender={1: "male", 2: "female"}.get(Payload.integer(data, "gender")),
            location="-".join(
                v for k in ("country", "province", "city") if (v := Payload.text(data, k))
            ),
        )
