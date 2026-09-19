import base64
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class AlipayProvider(AuthProvider):
    """RSA2 签名及公钥/证书序列号模式，共用应用 HTTP 资源，验证原始响应签名。"""

    capabilities = (
        ProviderCapability("ALIPAY", refresh=True),
        ProviderCapability("ALIPAY_CERT", refresh=True),
    )
    authorization_endpoint = "https://openauth.alipay.com/oauth2/publicAppAuthorize.htm"
    token_endpoint = "https://openapi.alipay.com/gateway.do"
    callback_code = "auth_code"
    client_parameter = "app_id"
    fixed_scopes = ("auth_user",)
    required_credentials = frozenset(("alipay_public_key",))
    allowed_options = frozenset(
        ("subject_type", "app_cert_sn", "alipay_root_cert_sn", "alipay_cert_sn")
    )
    required_options = frozenset(("subject_type",))
    profile_fields = {"username": "user_name", "nickname": "nick_name", "avatar": "avatar"}

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        if config.options["subject_type"] not in ("user_id", "open_id"):
            raise AuthException(Codes.CONFIG)
        if config.source == "ALIPAY_CERT":
            if set(config.options) != cls.allowed_options or any(
                re.fullmatch(
                    r"[0-9a-f]{32}(?:_[0-9a-f]{32})*"
                    if name == "alipay_root_cert_sn"
                    else r"[0-9a-f]{32}",
                    value,
                )
                is None
                for name, value in config.options.items()
                if name != "subject_type"
            ):
                raise AuthException(Codes.CONFIG)
        elif set(config.options) != {"subject_type"}:
            raise AuthException(Codes.CONFIG)
        cls._keys(config)

    @property
    def subject_field(self) -> str:
        return self.config.options["subject_type"]

    @staticmethod
    def _keys(config):
        try:
            private = serialization.load_pem_private_key(
                config.client_secret.get_secret_value().encode(), password=None
            )
            public = serialization.load_pem_public_key(
                config.credentials["alipay_public_key"].get_secret_value().encode()
            )
            if (
                not isinstance(private, rsa.RSAPrivateKey)
                or not isinstance(public, rsa.RSAPublicKey)
                or min(private.key_size, public.key_size) < 2048
            ):
                raise ValueError
            return private, public
        except (ValueError, TypeError) as error:
            raise AuthException(Codes.CONFIG, cause=error) from error

    async def _call(self, method, params, *, effect):
        private, public = self._keys(self.config)
        values = {
            "app_id": self.config.client_id,
            "method": method,
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "version": "1.0",
            "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"),
            **params,
        }
        if self.config.source == "ALIPAY_CERT":
            values.update(
                {name: self.config.options[name] for name in ("app_cert_sn", "alipay_root_cert_sn")}
            )
        canonical = "&".join(key + "=" + value for key, value in sorted(values.items()))
        values["sign"] = base64.b64encode(
            private.sign(canonical.encode(), padding.PKCS1v15(), hashes.SHA256())
        ).decode()
        raw = await self.http.request("POST", self.token_endpoint, effect=effect, data=values)
        response = self.http.decode_json(raw, effect=effect)
        key = method.replace(".", "_") + "_response"
        if "error_response" in response:
            raise AuthException(Codes.REJECTED, outcome="rejected")
        payload = Payload.object(response, key)
        signature = Payload.text(response, "sign", required=True)
        if (
            self.config.source == "ALIPAY_CERT"
            and response.get("alipay_cert_sn") != self.config.options["alipay_cert_sn"]
        ):
            raise AuthException(Codes.RESPONSE, outcome="unknown")
        try:
            signed_bytes = self._raw_member(raw.decode("utf-8"), key)
            public.verify(
                base64.b64decode(signature, validate=True),
                signed_bytes,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (ValueError, InvalidSignature, UnicodeError) as error:
            raise AuthException(Codes.RESPONSE, outcome="unknown", cause=error) from error
        if "code" in payload and Payload.text(payload, "code", required=True) != "10000":
            raise AuthException(Codes.REJECTED, outcome="rejected")
        return payload

    @staticmethod
    def _raw_member(text: str, wanted: str) -> bytes:
        """定位已解析且无重复字段的顶层成员，保留被签名 JSON 的精确字节。"""
        decoder = json.JSONDecoder()
        position = text.index("{") + 1
        while position < len(text):
            position += len(text[position:]) - len(text[position:].lstrip())
            name, position = decoder.raw_decode(text, position)
            position = text.index(":", position) + 1
            position += len(text[position:]) - len(text[position:].lstrip())
            start = position
            _, position = decoder.raw_decode(text, position)
            if name == wanted:
                return text[start:position].encode("utf-8")
            position += len(text[position:]) - len(text[position:].lstrip())
            if text[position] != ",":
                break
            position += 1
        raise ValueError("支付宝签名成员缺失")

    def authorization_parameters(self):
        values = super().authorization_parameters()
        del values["response_type"]
        return values

    async def exchange(self, code, flow):
        data = await self._call(
            "alipay.system.oauth.token",
            {"grant_type": "authorization_code", "code": code},
            effect=True,
        )
        return self.token(data)

    async def refresh(self, tokens):
        data = await self._call(
            "alipay.system.oauth.token",
            {"grant_type": "refresh_token", "refresh_token": self.refresh_value(tokens)},
            effect=True,
        )
        return self.token(data)

    async def userinfo(self, tokens):
        data = await self._call(
            "alipay.user.info.share", {"auth_token": self.access(tokens)}, effect=False
        )
        field = self.subject_field
        return self.identity(
            data,
            Payload.text(data, field, required=True),
            gender={"m": "male", "f": "female"}.get(Payload.text(data, "gender")),
            location=" ".join(v for k in ("province", "city") if (v := Payload.text(data, k))),
        )
