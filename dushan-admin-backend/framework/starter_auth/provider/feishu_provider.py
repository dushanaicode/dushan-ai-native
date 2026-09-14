from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class FeishuProvider(OAuthProvider):
    subject_field = "open_id"
    capabilities = (ProviderCapability("FEISHU", pkce=True, refresh=True, refresh_rotation=True),)
    authorization_endpoint = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
    token_endpoint = "https://accounts.feishu.cn/oauth/v3/token"
    userinfo_endpoint = "https://open.feishu.cn/open-apis/authen/v1/user_info"
    profile_fields = {
        "username": "name",
        "nickname": "name",
        "avatar": "avatar_url",
        "email": "email",
    }

    async def _token(self, params):
        data = await self.http.json(
            "POST", self.token_endpoint, effect=True, data={**self.client_fields(), **params}
        )
        if Payload.integer(data, "code", required=True) != 0:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        return self.token(
            data, refresh_expires_in=Payload.integer(data, "refresh_token_expires_in")
        )

    async def exchange(self, code, flow):
        return await self._token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.config.redirect_uri,
                "code_verifier": flow.verifier,
            }
        )

    async def refresh(self, tokens):
        return await self._token(
            {"grant_type": "refresh_token", "refresh_token": self.refresh_value(tokens)}
        )

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"Authorization": "Bearer " + self.access(tokens)},
        )
        if Payload.integer(data, "code", required=True) != 0:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        profile = Payload.object(data, "data")
        return self.identity(
            profile,
            Payload.text(profile, "open_id", required=True),
            union_id=Payload.text(profile, "union_id"),
        )
