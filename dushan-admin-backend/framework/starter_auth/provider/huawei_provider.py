import time

from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class HuaweiProvider(OAuthProvider):
    subject_field = "userID"
    capabilities = (ProviderCapability("HUAWEI", refresh=True),)
    authorization_endpoint = "https://oauth-login.cloud.huawei.com/oauth2/v2/authorize"
    token_endpoint = "https://oauth-login.cloud.huawei.com/oauth2/v2/token"
    userinfo_endpoint = "https://api.vmall.com/rest.php"
    profile_fields = {"username": "userName", "nickname": "userName", "avatar": "headPictureURL"}

    def authorization_parameters(self):
        return {**super().authorization_parameters(), "access_type": "offline"}

    async def userinfo(self, tokens):
        data = await self.http.json(
            "POST",
            self.userinfo_endpoint,
            data={
                "access_token": self.access(tokens),
                "nsp_ts": str(int(time.time() * 1000)),
                "nsp_fmt": "JS",
                "open_id": "OPENID",
                "nsp_svc": "huawei.oauth2.user.getTokenInfo",
            },
        )
        Payload.reject_errors(data)
        gender = Payload.integer(data, "gender")
        return self.identity(
            data, Payload.identifier(data, "userID"), gender={0: "male", 1: "female"}.get(gender)
        )
