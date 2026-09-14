from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class ToutiaoProvider(OAuthProvider):
    subject_field = "uid"
    capabilities = (ProviderCapability("TOUTIAO"),)
    authorization_endpoint = "https://open.snssdk.com/auth/authorize"
    token_endpoint = "https://open.snssdk.com/auth/token"
    userinfo_endpoint = "https://open.snssdk.com/data/user_profile"
    client_parameter = "client_key"
    fixed_scopes = ()
    profile_fields = {"avatar": "avatar_url", "remark": "description"}

    def authorization_parameters(self):
        return {**super().authorization_parameters(), "auth_only": "1", "display": "0"}

    async def exchange(self, code, flow):
        data = await self.http.json(
            "GET",
            self.token_endpoint,
            effect=True,
            params={
                "client_key": self.config.client_id,
                "client_secret": self.config.client_secret.get_secret_value(),
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        Payload.reject_errors(data)
        return self.token(data, subject=Payload.text(data, "open_id", required=True))

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            params={"client_key": self.config.client_id, "access_token": self.access(tokens)},
        )
        Payload.reject_errors(data)
        profile = Payload.object(data, "data")
        anonymous = Payload.integer(profile, "uid_type", required=True) == 14
        name = "匿名用户" if anonymous else Payload.text(profile, "screen_name", required=True)
        return self.identity(
            profile,
            Payload.identifier(profile, "uid"),
            username=name,
            nickname=name,
            snapshot_user=anonymous,
            gender={"male": "male", "female": "female"}.get(Payload.text(profile, "gender")),
        )
