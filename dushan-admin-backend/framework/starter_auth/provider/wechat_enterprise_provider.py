import re

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class WechatEnterpriseProvider(AuthProvider):
    subject_field = "userid"
    capabilities = tuple(
        ProviderCapability(source, token_kind="identity")
        for source in ("WECHAT_ENTERPRISE", "WECHAT_ENTERPRISE_WEB", "WECHAT_ENTERPRISE_CORP_APP")
    )
    token_endpoint = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    allowed_options = frozenset(("agent_id", "lang"))
    required_options = frozenset(("agent_id", "lang"))
    client_parameter = "appid"
    profile_fields = {
        "username": "name",
        "nickname": "alias",
        "avatar": "avatar",
        "location": "address",
        "email": "email",
    }

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        allowed = (
            (("snsapi_base",), ("snsapi_privateinfo",))
            if config.source == "WECHAT_ENTERPRISE_WEB"
            else ((),)
        )
        if (
            config.scopes not in allowed
            or re.fullmatch(r"[0-9]+", config.options["agent_id"]) is None
        ):
            raise AuthException(Codes.CONFIG)
        if config.options["lang"] not in ("zh", "en"):
            raise AuthException(Codes.CONFIG)

    @property
    def authorization_endpoint(self):
        return {
            "WECHAT_ENTERPRISE": "https://open.work.weixin.qq.com/wwopen/sso/qrConnect",
            "WECHAT_ENTERPRISE_WEB": "https://open.weixin.qq.com/connect/oauth2/authorize",
            "WECHAT_ENTERPRISE_CORP_APP": "https://login.work.weixin.qq.com/wwlogin/sso/login",
        }[self.config.source]

    def authorization_parameters(self):
        values = {
            **super().authorization_parameters(),
            "agentid": self.config.options["agent_id"],
            "lang": self.config.options["lang"],
        }
        if self.config.source == "WECHAT_ENTERPRISE_CORP_APP":
            values["login_type"] = "CorpApp"
            del values["response_type"]
        if self.config.source != "WECHAT_ENTERPRISE_WEB":
            del values["scope"]
        return values

    def authorize(self, flow, challenge):
        return super().authorize(flow, challenge) + "#wechat_redirect"

    async def _load_credential(self):
        data = await self.http.json(
            "GET",
            self.token_endpoint,
            effect=True,
            params={
                "corpid": self.config.client_id,
                "corpsecret": self.config.client_secret.get_secret_value(),
            },
        )
        Payload.reject_errors(data)
        return Payload.text(data, "access_token", required=True), Payload.integer(
            data, "expires_in", required=True
        )

    async def exchange(self, code, flow):
        credential = await self.credentials.get_or_load(self.config, self._load_credential)
        modern = self.config.source == "WECHAT_ENTERPRISE_CORP_APP"
        endpoint = "auth/getuserinfo" if modern else "user/getuserinfo"
        data = await self.http.json(
            "GET",
            "https://qyapi.weixin.qq.com/cgi-bin/" + endpoint,
            effect=True,
            params={"access_token": credential, "code": code},
        )
        Payload.reject_errors(data)
        subject = Payload.text(data, "userid" if modern else "UserId", required=True)
        try:
            if not modern:
                profile = await self.http.json(
                    "GET",
                    "https://qyapi.weixin.qq.com/cgi-bin/user/get",
                    params={"access_token": credential, "userid": subject},
                )
                Payload.reject_errors(profile)
                if Payload.text(profile, "userid", required=True) != subject:
                    raise AuthException(Codes.BINDING)
                ticket = Payload.text(
                    data, "user_ticket", required="snsapi_privateinfo" in self.config.scopes
                )
                if ticket:
                    detail = await self.http.json(
                        "POST",
                        "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail",
                        params={"access_token": credential},
                        json={"user_ticket": ticket},
                        effect=True,
                    )
                    Payload.reject_errors(detail)
                    if Payload.text(detail, "userid", required=True) != subject:
                        raise AuthException(Codes.BINDING)
                    profile.update(detail)
                data = profile
        except AuthException as error:
            # 授权码已在 getuserinfo 成功消费，之后的资料失败不能宣称尚未发送。
            raise AuthException(error.error_code, outcome="unknown", cause=error) from error
        # 应用级凭据只留在应用 Cache，不作为用户凭据交给消费者。
        return self.tokens(subject=subject, data=data)

    async def userinfo(self, tokens):
        return self.identity(
            tokens.data,
            tokens.subject,
            gender={1: "male", 2: "female"}.get(Payload.integer(tokens.data, "gender")),
        )
