from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class DingtalkV2Provider(OAuthProvider):
    subject_field = "openId"
    capabilities = (ProviderCapability("DINGTALK_V2", refresh=True),)
    authorization_endpoint = "https://login.dingtalk.com/oauth2/auth"
    token_endpoint = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
    userinfo_endpoint = "https://api.dingtalk.com/v1.0/contact/users/me"
    callback_code = "authCode"
    allowed_options = frozenset(("org_type", "corp_id", "exclusive_login", "exclusive_corp_id"))
    profile_fields = {"username": "nick", "nickname": "nick", "avatar": "avatarUrl"}

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        if config.scopes not in (("openid",), ("openid", "corpid")):
            raise AuthException(Codes.CONFIG)
        if "exclusive_login" in config.options and config.options["exclusive_login"] not in (
            "true",
            "false",
        ):
            raise AuthException(Codes.CONFIG)

    def authorization_parameters(self):
        result = {**super().authorization_parameters(), "prompt": "consent"}
        for key, name in {
            "org_type": "org_type",
            "corp_id": "corpId",
            "exclusive_login": "exclusiveLogin",
            "exclusive_corp_id": "exclusiveCorpId",
        }.items():
            if key in self.config.options:
                result[name] = self.config.options[key]
        return result

    async def _token(self, values):
        data = await self.http.json(
            "POST",
            self.token_endpoint,
            effect=True,
            json={
                "clientId": self.config.client_id,
                "clientSecret": self.config.client_secret.get_secret_value(),
                **values,
            },
        )
        Payload.reject_errors(data)
        return self.tokens(
            access_token=Payload.text(data, "accessToken", required=True),
            refresh_token=Payload.text(data, "refreshToken"),
            expires_in=Payload.integer(data, "expireIn", required=True),
        )

    async def exchange(self, code, flow):
        return await self._token({"grantType": "authorization_code", "code": code})

    async def refresh(self, tokens):
        return await self._token(
            {"grantType": "refresh_token", "refreshToken": self.refresh_value(tokens)}
        )

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"x-acs-dingtalk-access-token": self.access(tokens)},
        )
        if "code" in data:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        return self.identity(
            data,
            Payload.text(data, "openId", required=True),
            union_id=Payload.text(data, "unionId"),
            snapshot_user=Payload.boolean(data, "visitor") is True,
        )
