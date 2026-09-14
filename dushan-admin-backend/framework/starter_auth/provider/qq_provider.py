import re
from urllib.parse import parse_qsl

from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class QqProvider(OAuthProvider):
    subject_field = "openid"
    capabilities = (ProviderCapability("QQ", refresh=True, refresh_rotation=True),)
    authorization_endpoint = "https://graph.qq.com/oauth2.0/authorize"
    token_endpoint = "https://graph.qq.com/oauth2.0/token"
    userinfo_endpoint = "https://graph.qq.com/user/get_user_info"
    allowed_options = frozenset(("union_id",))
    scope_separator = ","
    profile_fields = {"username": "nickname", "nickname": "nickname"}

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        if "union_id" in config.options and config.options["union_id"] not in ("true", "false"):
            raise AuthException(Codes.CONFIG)

    async def _token(self, params):
        raw = await self.http.request(
            "GET", self.token_endpoint, effect=True, params={**self.client_fields(), **params}
        )
        try:
            pairs = parse_qsl(raw.decode("utf-8"), strict_parsing=True, max_num_fields=32)
            data = self.http.unique_object(pairs)
        except (ValueError, UnicodeError) as error:
            raise AuthException(Codes.RESPONSE, outcome="unknown", cause=error) from error
        return self.token(data)

    async def exchange(self, code, flow):
        return await self._token(
            {
                "code": code,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            }
        )

    async def refresh(self, tokens):
        return await self._token(
            {"refresh_token": self.refresh_value(tokens), "grant_type": "refresh_token"}
        )

    async def userinfo(self, tokens):
        raw = await self.http.request(
            "GET",
            "https://graph.qq.com/oauth2.0/me",
            params={
                "access_token": self.access(tokens),
                "unionid": "1" if self.config.options.get("union_id") == "true" else "0",
            },
        )
        match = re.fullmatch(rb"\s*callback\s*\(\s*(\{.*\})\s*\);?\s*", raw, flags=re.DOTALL)
        if match is None:
            raise AuthException(Codes.RESPONSE)
        identity = self.http.decode_json(match[1])
        Payload.reject_errors(identity)
        if Payload.text(identity, "client_id", required=True) != self.config.client_id:
            raise AuthException(Codes.BINDING)
        subject = Payload.text(identity, "openid", required=True)
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            params={
                "access_token": self.access(tokens),
                "oauth_consumer_key": self.config.client_id,
                "openid": subject,
            },
        )
        if Payload.integer(data, "ret", required=True) != 0:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        return self.identity(
            data,
            subject,
            union_id=Payload.text(identity, "unionid"),
            avatar=Payload.text(data, "figureurl_qq_2") or Payload.text(data, "figureurl_qq_1"),
            location="-".join(v for k in ("province", "city") if (v := Payload.text(data, k))),
            gender={"男": "male", "女": "female"}.get(Payload.text(data, "gender")),
        )
