import base64
import json
import time

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class AppleProvider(OAuthProvider):
    """Apple Sign in with Apple，使用 .p8 私钥生成 JWT client secret。

    官方资料：
    - REST: https://developer.apple.com/documentation/signinwithapplerestapi
    - 环境配置: https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple
    - Discovery: https://appleid.apple.com/.well-known/openid-configuration
    """

    subject_field = "sub"
    capabilities = (ProviderCapability("APPLE", oidc=True, refresh=True),)
    authorization_endpoint = "https://appleid.apple.com/auth/authorize"
    token_endpoint = "https://appleid.apple.com/auth/token"
    userinfo_endpoint = ""
    allowed_options = frozenset(("team_id", "key_id"))
    required_options = frozenset(("team_id", "key_id"))
    oidc_metadata = OidcMetadata(
        issuer="https://appleid.apple.com",
        jwks_uri="https://appleid.apple.com/auth/keys",
        algorithms=("RS256",),
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        discovery_uri="https://appleid.apple.com/.well-known/openid-configuration",
    )

    def authorization_parameters(self):
        parameters = super().authorization_parameters()
        if {"name", "email"} & set(self.config.scopes):
            # 申请 name/email 时 Apple 要求 response_mode=form_post，否则返回 invalid_request；
            # 此时回调以 POST 表单送达，业务需按表单参数转交 complete。
            parameters["response_mode"] = "form_post"
        return parameters

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @classmethod
    def _client_secret(cls, config) -> str:
        try:
            key = serialization.load_pem_private_key(
                config.client_secret.get_secret_value().encode(), password=None
            )
            if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(
                key.curve, ec.SECP256R1
            ):
                raise ValueError("Apple client secret 必须使用 P-256 私钥")
            now = int(time.time())
            header = {"alg": "ES256", "kid": config.options["key_id"], "typ": "JWT"}
            claims = {
                "iss": config.options["team_id"],
                "iat": now,
                "exp": now + 180 * 24 * 60 * 60,
                "aud": "https://appleid.apple.com",
                "sub": config.client_id,
            }
            encoded_header = cls._encode(json.dumps(header, separators=(",", ":")).encode())
            encoded_claims = cls._encode(json.dumps(claims, separators=(",", ":")).encode())
            signing_input = f"{encoded_header}.{encoded_claims}"
            signature = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(signature)
            encoded_signature = cls._encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
            return f"{signing_input}.{encoded_signature}"
        except (TypeError, ValueError, UnsupportedAlgorithm, KeyError) as error:
            raise AuthException(Codes.CONFIG, cause=error) from error

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        cls._client_secret(config)

    def client_fields(self):
        return {
            "client_id": self.config.client_id,
            "client_secret": self._client_secret(self.config),
        }

    async def userinfo(self, tokens):
        if tokens.claims is None:
            raise AuthException(Codes.OIDC)
        return self.identity(
            tokens.claims,
            tokens.subject,
            issuer=self.oidc_metadata.issuer,
            username=Payload.text(tokens.claims, "email"),
            email=Payload.text(tokens.claims, "email"),
            email_verified=Payload.boolean(tokens.claims, "email_verified"),
        )
