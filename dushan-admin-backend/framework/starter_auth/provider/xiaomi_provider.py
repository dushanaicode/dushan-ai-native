from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class XiaomiProvider(OAuthProvider):
    subject_field = "openId"
    capabilities = (ProviderCapability("MI", refresh=True),)
    authorization_endpoint = "https://account.xiaomi.com/oauth2/authorize"
    token_endpoint = "https://account.xiaomi.com/oauth2/token"
    userinfo_endpoint = "https://open.account.xiaomi.com/user/profile"
    profile_fields = {
        "username": "miliaoNick",
        "nickname": "miliaoNick",
        "avatar": "miliaoIcon",
        "email": "mail",
    }

    def authorization_parameters(self):
        return {**super().authorization_parameters(), "skip_confirm": "false"}

    async def _token(self, params):
        raw = await self.http.request(
            "GET",
            self.token_endpoint,
            effect=True,
            params={**self.client_fields(), "redirect_uri": self.config.redirect_uri, **params},
        )
        data = self.http.decode_json(raw.removeprefix(b"&&&START&&&"), effect=True)
        Payload.reject_errors(data)
        return self.token(data, subject=Payload.text(data, "openId", required=True))

    async def exchange(self, code, flow):
        return await self._token({"code": code, "grant_type": "authorization_code"})

    async def refresh(self, tokens):
        refreshed = await self._token(
            {"refresh_token": self.refresh_value(tokens), "grant_type": "refresh_token"}
        )
        return refreshed

    async def userinfo(self, tokens):
        params = {"clientId": self.config.client_id, "token": self.access(tokens)}
        data = await self.http.json("GET", self.userinfo_endpoint, params=params)
        if data.get("result") != "ok":
            raise AuthException(Codes.REJECTED, outcome="rejected")
        profile = Payload.object(data, "data")
        values = {}
        if "user/phoneAndEmail" in self.config.scopes:
            email = await self.http.json(
                "GET", "https://open.account.xiaomi.com/user/phoneAndEmail", params=params
            )
            if email.get("result") != "ok":
                raise AuthException(Codes.REJECTED, outcome="rejected")
            values["email"] = Payload.text(Payload.object(email, "data"), "email")
        return self.identity(profile, tokens.subject, **values)
