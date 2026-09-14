from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class WechatProvider(OAuthProvider):
    subject_field = "openid"
    capabilities = (
        ProviderCapability("WECHAT_OPEN", refresh=True),
        ProviderCapability("WECHAT_MP", refresh=True),
    )
    token_endpoint = "https://api.weixin.qq.com/sns/oauth2/access_token"
    userinfo_endpoint = "https://api.weixin.qq.com/sns/userinfo"
    refresh_endpoint = "https://api.weixin.qq.com/sns/oauth2/refresh_token"
    client_parameter = "appid"
    scope_separator = ","
    profile_fields = {"username": "nickname", "nickname": "nickname", "avatar": "headimgurl"}

    @property
    def authorization_endpoint(self):
        return (
            "https://open.weixin.qq.com/connect/qrconnect"
            if self.config.source == "WECHAT_OPEN"
            else "https://open.weixin.qq.com/connect/oauth2/authorize"
        )

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        valid = (
            (("snsapi_login",),)
            if config.source == "WECHAT_OPEN"
            else (("snsapi_base",), ("snsapi_userinfo",))
        )
        if config.scopes not in valid:
            raise AuthException(Codes.CONFIG)

    def authorize(self, flow, challenge):
        return super().authorize(flow, challenge) + "#wechat_redirect"

    async def exchange(self, code, flow):
        data = await self.http.json(
            "GET",
            self.token_endpoint,
            effect=True,
            params={
                "appid": self.config.client_id,
                "secret": self.config.client_secret.get_secret_value(),
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        Payload.reject_errors(data)
        return self.token(data, subject=Payload.text(data, "openid", required=True))

    async def refresh(self, tokens):
        data = await self.http.json(
            "GET",
            self.refresh_endpoint,
            effect=True,
            params={
                "appid": self.config.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_value(tokens),
            },
        )
        Payload.reject_errors(data)
        refreshed = self.token(data, subject=Payload.text(data, "openid", required=True))
        return refreshed

    async def userinfo(self, tokens):
        snapshot = Payload.integer(tokens.data, "is_snapshotuser") == 1
        if self.config.source == "WECHAT_MP":
            scopes = set((tokens.scope or "").split(","))
            if "snsapi_userinfo" not in scopes:
                if scopes != {"snsapi_base"}:
                    raise AuthException(Codes.RESPONSE)
                return self.identity({}, tokens.subject, snapshot_user=snapshot)
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            params={
                "access_token": self.access(tokens),
                "openid": tokens.subject,
                "lang": "zh_CN",
            },
        )
        Payload.reject_errors(data)
        if Payload.text(data, "openid", required=True) != tokens.subject:
            raise AuthException(Codes.BINDING)
        return self.identity(
            data,
            tokens.subject,
            union_id=Payload.text(data, "unionid"),
            snapshot_user=snapshot,
            gender={1: "male", 2: "female"}.get(Payload.integer(data, "sex")),
            location="-".join(
                v for k in ("country", "province", "city") if (v := Payload.text(data, k))
            ),
        )
