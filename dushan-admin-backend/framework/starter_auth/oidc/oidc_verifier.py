import base64
import hashlib
import hmac
import math
import re
import time

from joserfc import jws, jwt
from joserfc.errors import BadSignatureError, InvalidKeyIdError, JoseError
from joserfc.jwk import KeySet

from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.oidc.jwks_entry import JwksEntry
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata


class OidcVerifier:
    """使用 JOSE 库验证签名与声明；轮换只重读公钥，不重放授权码或刷新请求。"""

    def __init__(self, http, settings):
        self.http, self.settings = http, settings
        self._entries: dict[OidcMetadata, JwksEntry] = {}

    async def verify(
        self,
        encoded: str,
        metadata: OidcMetadata,
        audience: str,
        nonce: str | None,
        *,
        access_token: str,
        code: str | None = None,
        expected_subject: str | None = None,
        previous_claims: dict | None = None,
    ) -> dict:
        try:
            refreshing = expected_subject is not None
            if not refreshing and not nonce:
                raise AuthException(Codes.OIDC)
            header = jws.extract_compact(encoded.encode("ascii")).headers()
            if (
                header.get("alg") not in metadata.algorithms
                or not isinstance(header.get("kid"), str)
                or re.fullmatch(r"[!-~]{1,256}", header["kid"]) is None
                or {"jku", "x5u", "jwk", "x5c"}.intersection(header)
            ):
                raise AuthException(Codes.OIDC)
            keys, generation = await self._keys(metadata)
            try:
                token = jwt.decode(encoded, keys, algorithms=list(metadata.algorithms))
            except (InvalidKeyIdError, BadSignatureError):
                keys, _ = await self._keys(metadata, generation)
                token = jwt.decode(encoded, keys, algorithms=list(metadata.algorithms))
            claims = token.claims
            for name in ("exp", "iat", "nbf", "auth_time"):
                if name in claims and (
                    type(claims[name]) not in (int, float)
                    or (type(claims[name]) is float and not math.isfinite(claims[name]))
                ):
                    raise AuthException(Codes.OIDC)
            nonce_rule = {"essential": not refreshing}
            if nonce is not None:
                nonce_rule["value"] = nonce
            jwt.JWTClaimsRegistry(
                leeway=self.settings.oidc_leeway_seconds,
                iss={"essential": True, "value": metadata.issuer},
                aud={"essential": True, "value": audience},
                sub={"essential": True},
                exp={"essential": True},
                iat={"essential": True},
                nonce=nonce_rule,
            ).validate(claims)
            if (
                not isinstance(claims["sub"], str)
                or not claims["sub"]
                or claims["iss"] != metadata.issuer
                or claims["exp"] <= claims["iat"]
                or not isinstance(claims["aud"], (str, list))
            ):
                raise AuthException(Codes.OIDC)
            # JWTClaimsRegistry 的 value 支持集合包含；nonce 必须是同一标量字符串。
            if "nonce" in claims and (
                not isinstance(claims["nonce"], str)
                or not claims["nonce"]
                or (nonce is not None and not hmac.compare_digest(claims["nonce"], nonce))
            ):
                raise AuthException(Codes.OIDC)
            aud = claims["aud"]
            if isinstance(aud, list) and (
                not aud or any(not isinstance(v, str) or not v for v in aud)
            ):
                raise AuthException(Codes.OIDC)
            if (isinstance(aud, list) and len(aud) > 1) or "azp" in claims:
                if claims.get("azp") != audience:
                    raise AuthException(Codes.OIDC)
            if refreshing:
                if claims["sub"] != expected_subject:
                    raise AuthException(Codes.OIDC)
                if previous_claims is not None:
                    old_aud = previous_claims["aud"]
                    if set(aud if isinstance(aud, list) else (aud,)) != set(
                        old_aud if isinstance(old_aud, list) else (old_aud,)
                    ):
                        raise AuthException(Codes.OIDC)
                    if claims["iss"] != previous_claims["iss"]:
                        raise AuthException(Codes.OIDC)
                    if "auth_time" in claims and claims["auth_time"] != previous_claims.get(
                        "auth_time"
                    ):
                        raise AuthException(Codes.OIDC)
            for field, value in (("at_hash", access_token), ("c_hash", code)):
                if field in claims:
                    if value is None:
                        raise AuthException(Codes.OIDC)
                    digest = hashlib.new("sha" + header["alg"][-3:], value.encode("ascii")).digest()
                    expected = (
                        base64.urlsafe_b64encode(digest[: len(digest) // 2]).rstrip(b"=").decode()
                    )
                    if not isinstance(claims[field], str) or not hmac.compare_digest(
                        expected, claims[field]
                    ):
                        raise AuthException(Codes.OIDC)
            return claims
        except (JoseError, ValueError, TypeError, KeyError, UnicodeError) as error:
            raise AuthException(Codes.OIDC, cause=error) from error

    async def _keys(self, metadata: OidcMetadata, generation: int | None = None):
        entry = self._entries.setdefault(metadata, JwksEntry())
        async with entry.lock:
            now = time.monotonic()
            if generation is not None:
                if generation != entry.generation or now < entry.refresh_after:
                    return entry.keys, entry.generation
                entry.refresh_after = now + self.settings.jwks_refresh_cooldown_seconds
            elif entry.keys is not None and now < entry.expires_at:
                return entry.keys, entry.generation
            if now < entry.retry_after:
                raise AuthException(Codes.OIDC)
            entry.retry_after = now + self.settings.jwks_refresh_cooldown_seconds
            await self._discovery(metadata, entry, now)
            payload = await self.http.json("GET", metadata.jwks_uri)
            entry.keys = self._import_keys(payload, metadata)
            entry.generation += 1
            entry.expires_at = time.monotonic() + self.settings.jwks_ttl_seconds
            entry.retry_after = 0
            return entry.keys, entry.generation

    async def _discovery(self, metadata, entry, now):
        for url in (metadata.issuer, metadata.jwks_uri):
            AuthUrlPolicy.require(url, allow_loopback_http=self.settings.allow_loopback_http)
        if metadata.discovery_uri is None or now < entry.discovery_expires_at:
            return
        values = await self.http.json("GET", metadata.discovery_uri)
        expected = {
            "issuer": metadata.issuer,
            "jwks_uri": metadata.jwks_uri,
            "authorization_endpoint": metadata.authorization_endpoint,
            "token_endpoint": metadata.token_endpoint,
        }
        if any(values.get(key) != value for key, value in expected.items()):
            raise AuthException(Codes.OIDC)
        if not set(metadata.algorithms).issubset(
            values.get("id_token_signing_alg_values_supported", ())
        ):
            raise AuthException(Codes.OIDC)
        entry.discovery_expires_at = now + self.settings.jwks_ttl_seconds

    def _import_keys(self, payload, metadata):
        keys = payload.get("keys")
        if not isinstance(keys, list) or not 1 <= len(keys) <= self.settings.jwks_max_keys:
            raise AuthException(Codes.OIDC)
        seen = set()
        for key in keys:
            if (
                not isinstance(key, dict)
                or key.get("kty") not in ("RSA", "EC")
                or not isinstance(key.get("kid"), str)
                or not key["kid"]
                or key["kid"] in seen
                or {"d", "p", "q", "dp", "dq", "qi", "oth", "k"}.intersection(key)
                or key.get("use", "sig") != "sig"
                or key.get("key_ops", ["verify"]) != ["verify"]
                or ("alg" in key and key["alg"] not in metadata.algorithms)
            ):
                raise AuthException(Codes.OIDC)
            seen.add(key["kid"])
        return KeySet.import_key_set({"keys": keys})
