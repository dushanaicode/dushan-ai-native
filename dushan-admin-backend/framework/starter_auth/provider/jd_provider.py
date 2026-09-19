import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class JdProvider(OAuthProvider):
    subject_field = "open_id"
    capabilities = (ProviderCapability("JD", refresh=True),)
    authorization_endpoint = "https://open-oauth.jd.com/oauth2/to_login"
    token_endpoint = "https://open-oauth.jd.com/oauth2/access_token"
    refresh_endpoint = "https://open-oauth.jd.com/oauth2/refresh_token"
    userinfo_endpoint = "https://api.jd.com/routerjson"
    client_parameter = "app_key"
    profile_fields = {"username": "nickName", "nickname": "nickName", "avatar": "imageUrl"}

    def client_fields(self):
        return {
            "app_key": self.config.client_id,
            "app_secret": self.config.client_secret.get_secret_value(),
        }

    def token(self, data, **values):
        return super().token(data, subject=Payload.text(data, "open_id"), **values)

    @staticmethod
    def signature(secret, params):
        text = secret + "".join(key + str(value) for key, value in sorted(params.items())) + secret
        return hashlib.md5(text.encode()).hexdigest().upper()

    async def userinfo(self, tokens):
        if tokens.subject is None:
            raise AuthException(Codes.RESPONSE)
        params = {
            "access_token": self.access(tokens),
            "app_key": self.config.client_id,
            "method": "jingdong.user.getUserInfoByOpenId",
            "v": "2.0",
            "360buy_param_json": json.dumps({"openId": tokens.subject}, separators=(",", ":")),
            "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"),
        }
        params["sign"] = self.signature(self.config.client_secret.get_secret_value(), params)
        data = await self.http.json("POST", self.userinfo_endpoint, data=params)
        Payload.reject_errors(data)
        outer = Payload.object(data, "jingdong_user_getUserInfoByOpenId_response")
        result = Payload.object(outer, "getuserinfobyappidandopenid_result")
        profile = Payload.object(result, "data")
        return self.identity(
            profile,
            tokens.subject,
            gender={"m": "male", "f": "female"}.get(Payload.text(profile, "gendar")),
        )
