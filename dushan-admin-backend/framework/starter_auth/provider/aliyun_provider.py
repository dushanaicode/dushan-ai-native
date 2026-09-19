from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class AliyunProvider(OAuthProvider):
    subject_field = "sub"
    capabilities = (ProviderCapability("ALIYUN", oidc=True, refresh=True),)
    authorization_endpoint = "https://signin.aliyun.com/oauth2/v1/auth"
    token_endpoint = "https://oauth.aliyun.com/v1/token"
    userinfo_endpoint = "https://oauth.aliyun.com/v1/userinfo"
    oidc_metadata = OidcMetadata(
        "https://oauth.aliyun.com",
        "https://oauth.aliyun.com/v1/keys",
        ("RS256",),
        authorization_endpoint,
        token_endpoint,
    )
    profile_fields = {"username": "login_name", "nickname": "name"}

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"Authorization": "Bearer " + self.access(tokens)},
        )
        Payload.reject_errors(data)
        subject = Payload.text(data, "sub", required=True)
        if subject != tokens.subject:
            raise AuthException(Codes.BINDING)
        return self.identity(data, subject, issuer=self.oidc_metadata.issuer)
