import base64
import hashlib
import hmac
import time

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class DingtalkProvider(AuthProvider):
    subject_field = "openid"
    capabilities = tuple(
        ProviderCapability(source, token_kind="identity")
        for source in ("DINGTALK", "DINGTALK_ACCOUNT")
    )
    userinfo_endpoint = "https://oapi.dingtalk.com/sns/getuserinfo_bycode"
    client_parameter = "appid"
    fixed_scopes = ("snsapi_login",)
    profile_fields = {"username": "nick", "nickname": "nick"}

    @property
    def authorization_endpoint(self):
        return (
            "https://oapi.dingtalk.com/connect/qrconnect"
            if self.config.source == "DINGTALK"
            else "https://oapi.dingtalk.com/connect/oauth2/sns_authorize"
        )

    async def exchange(self, code, flow):
        timestamp = str(int(time.time() * 1000))
        signature = base64.b64encode(
            hmac.new(
                self.config.client_secret.get_secret_value().encode(),
                timestamp.encode(),
                hashlib.sha256,
            ).digest()
        ).decode()
        data = await self.http.json(
            "POST",
            self.userinfo_endpoint,
            effect=True,
            params={
                "signature": signature,
                "timestamp": timestamp,
                "accessKey": self.config.client_id,
            },
            json={"tmp_auth_code": code},
        )
        if Payload.integer(data, "errcode", required=True) != 0:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        profile = Payload.object(data, "user_info")
        return self.tokens(
            subject=Payload.text(profile, "openid", required=True),
            union_id=Payload.text(profile, "unionid"),
            data=profile,
        )

    async def userinfo(self, tokens):
        return self.identity(tokens.data, tokens.subject, union_id=tokens.union_id)
