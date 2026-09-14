from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class HuaweiV3Provider(OAuthProvider):
    subject_field = "sub"
    capabilities = (ProviderCapability("HUAWEI_V3", pkce=True, oidc=True, refresh=True),)
    authorization_endpoint = "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
    token_endpoint = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
    userinfo_endpoint = "https://account.cloud.huawei.com/rest.php"
    oidc_metadata = OidcMetadata(
        "https://accounts.huawei.com",
        "https://oauth-login.cloud.huawei.com/oauth2/v3/certs",
        ("RS256", "PS256"),
        authorization_endpoint,
        token_endpoint,
    )
    profile_fields = {
        "username": "name",
        "nickname": "nickname",
        "avatar": "picture",
        "email": "email",
    }

    def authorization_parameters(self):
        return {
            **super().authorization_parameters(),
            "access_type": "offline",
            "response_mode": "form_post",
        }

    async def userinfo(self, tokens):
        if tokens.claims is None:
            raise AuthException(Codes.OIDC)
        if "https://www.huawei.com/auth/account/base.profile" in self.config.scopes:
            profile = await self.http.json(
                "POST",
                self.userinfo_endpoint,
                data={
                    "access_token": self.access(tokens),
                    "getNickName": "1",
                    "nsp_svc": "GOpen.User.getInfo",
                },
            )
            Payload.reject_errors(profile)
            return self.identity(
                {},
                tokens.subject,
                issuer=self.oidc_metadata.issuer,
                union_id=Payload.text(profile, "unionID", required=True),
                username=Payload.text(profile, "displayName"),
                nickname=Payload.text(profile, "displayName"),
                avatar=Payload.text(profile, "headPictureURL"),
            )
        return self.identity(
            tokens.claims,
            tokens.subject,
            issuer=self.oidc_metadata.issuer,
            email_verified=Payload.boolean(tokens.claims, "email_verified"),
        )
