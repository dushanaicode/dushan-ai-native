from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class CsdnProvider(OAuthProvider):
    expires_required = False
    subject_field = "username"
    capabilities = (ProviderCapability("CSDN"),)
    authorization_endpoint = "https://api.csdn.net/oauth2/authorize"
    token_endpoint = "https://api.csdn.net/oauth2/access_token"
    userinfo_endpoint = "https://api.csdn.net/user/getinfo"
    fixed_scopes = ()
    profile_fields = {"username": "username", "remark": "description", "blog": "website"}

    async def exchange(self, code, flow):
        data = await self.http.json(
            "POST",
            self.token_endpoint,
            effect=True,
            params={
                **self.client_fields(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.config.redirect_uri,
            },
        )
        return self.token(data)

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET", self.userinfo_endpoint, params={"access_token": self.access(tokens)}
        )
        Payload.reject_errors(data)
        return self.identity(data, Payload.text(data, "username", required=True))
