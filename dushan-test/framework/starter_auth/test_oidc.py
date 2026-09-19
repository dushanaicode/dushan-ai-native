import asyncio
import base64
import hashlib
import time

import pytest
from joserfc import jwt

from framework.starter_auth.core.auth_http_client import AuthHttpClient
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.oidc.oidc_verifier import OidcVerifier

from .support import ACCESS, FLOW, RecordingTransport, oidc_token, rsa_key, settings

META = OidcMetadata(
    "https://issuer.example",
    "https://issuer.example/keys",
    ("RS256",),
    "https://issuer.example/authorize",
    "https://issuer.example/token",
)


@pytest.fixture(scope="module")
def key():
    return rsa_key()


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://other.example"},
        {"aud": "other-client"},
        {"exp": 100},
        {"iat": int(time.time()) + 1000},
        {"nbf": int(time.time()) + 1000},
        {"nonce": "wrong"},
        {"nonce": [FLOW.nonce]},
        {"nonce": None},
        {"sub": ""},
        {"sub": 123},
        {"exp": True},
        {"iat": "not-a-number"},
        {"aud": ["client-a", "second"]},
        {"azp": "second"},
        {"at_hash": "wrong"},
    ],
)
async def test_oidc_rejects_wrong_claims(key, claims):
    transport = RecordingTransport([{"keys": [key.as_dict(private=False)]}])
    http = AuthHttpClient(settings(oidc_leeway_seconds=0), transport=transport)
    verifier = OidcVerifier(http, settings(oidc_leeway_seconds=0))
    try:
        encoded = oidc_token(key, META, FLOW.nonce, **claims)
        with pytest.raises(AuthException) as failure:
            await verifier.verify(encoded, META, "client-a", FLOW.nonce, access_token=ACCESS)
        assert failure.value.error_code == Codes.OIDC
        assert len(transport.requests) == 1
    finally:
        await http.close()


@pytest.mark.parametrize("missing", ["iss", "aud", "sub", "exp", "iat", "nonce"])
async def test_oidc_required_claims(key, missing):
    values = {
        "iss": META.issuer,
        "aud": "client-a",
        "sub": "123",
        "exp": int(time.time()) + 600,
        "iat": int(time.time()),
        "nonce": FLOW.nonce,
    }
    values.pop(missing)
    encoded = jwt.encode({"alg": "RS256", "kid": key.kid}, values, key)
    http = AuthHttpClient(
        settings(), transport=RecordingTransport([{"keys": [key.as_dict(private=False)]}])
    )
    try:
        with pytest.raises(AuthException):
            await OidcVerifier(http, settings()).verify(
                encoded, META, "client-a", FLOW.nonce, access_token=ACCESS
            )
    finally:
        await http.close()


async def test_oidc_valid_multiple_audience_and_token_hashes(key):
    def half_hash(value):
        return (
            base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()[:16])
            .rstrip(b"=")
            .decode()
        )

    encoded = oidc_token(
        key,
        META,
        FLOW.nonce,
        aud=["client-a", "second"],
        azp="client-a",
        at_hash=half_hash(ACCESS),
        c_hash=half_hash("code"),
    )
    http = AuthHttpClient(
        settings(), transport=RecordingTransport([{"keys": [key.as_dict(private=False)]}])
    )
    try:
        claims = await OidcVerifier(http, settings()).verify(
            encoded, META, "client-a", FLOW.nonce, access_token=ACCESS, code="code"
        )
        assert claims["sub"] == "external-subject"
    finally:
        await http.close()


async def test_jwks_cache_rotation_single_fetch_for_concurrent_callbacks(key):
    rotated = rsa_key("rotated")
    transport = RecordingTransport(
        [{"keys": [key.as_dict(private=False)]}, {"keys": [rotated.as_dict(private=False)]}]
    )
    http = AuthHttpClient(settings(), transport=transport)
    verifier = OidcVerifier(http, settings())
    try:
        old = oidc_token(key, META, FLOW.nonce)
        await verifier.verify(old, META, "client-a", FLOW.nonce, access_token=ACCESS)
        await verifier.verify(old, META, "client-a", FLOW.nonce, access_token=ACCESS)
        new = oidc_token(rotated, META, FLOW.nonce)
        results = await asyncio.gather(
            *(
                verifier.verify(new, META, "client-a", FLOW.nonce, access_token=ACCESS)
                for _ in range(20)
            )
        )
        assert all(c["sub"] == "external-subject" for c in results)
        assert len(transport.requests) == 2
    finally:
        await http.close()


async def test_jwks_same_kid_rotation_and_invalid_signature_cooldown(key):
    rotated = rsa_key(key.kid)
    transport = RecordingTransport(
        [{"keys": [key.as_dict(private=False)]}, {"keys": [rotated.as_dict(private=False)]}]
    )
    http = AuthHttpClient(settings(), transport=transport)
    verifier = OidcVerifier(http, settings())
    try:
        await verifier.verify(
            oidc_token(key, META, FLOW.nonce), META, "client-a", FLOW.nonce, access_token=ACCESS
        )
        await verifier.verify(
            oidc_token(rotated, META, FLOW.nonce), META, "client-a", FLOW.nonce, access_token=ACCESS
        )
        for _ in range(4):
            with pytest.raises(AuthException):
                await verifier.verify(
                    oidc_token(key, META, FLOW.nonce),
                    META,
                    "client-a",
                    FLOW.nonce,
                    access_token=ACCESS,
                )
        assert len(transport.requests) == 2
    finally:
        await http.close()


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "too_many",
        "duplicate",
        "private",
        "partial_private",
        "symmetric",
        "encryption",
        "algorithm",
        "broken",
    ],
)
async def test_malformed_jwks_rejected_and_negative_cached(key, kind):
    public = key.as_dict(private=False)
    choices = {
        "empty": [],
        "too_many": [public] * 33,
        "duplicate": [public, public],
        "private": [key.as_dict(private=True)],
        "partial_private": [{**public, "p": "private-factor"}],
        "symmetric": [{"kty": "oct", "kid": "key-one", "k": "AAAA"}],
        "encryption": [{**public, "use": "enc"}],
        "algorithm": [{**public, "alg": "HS256"}],
        "broken": [{"kid": "key-one", "kty": "RSA", "n": "!", "e": "!"}],
    }
    transport = RecordingTransport([{"keys": choices[kind]}])
    http = AuthHttpClient(settings(), transport=transport)
    verifier = OidcVerifier(http, settings())
    try:
        for _ in range(2):
            with pytest.raises(AuthException):
                await verifier.verify(
                    oidc_token(key, META, FLOW.nonce),
                    META,
                    "client-a",
                    FLOW.nonce,
                    access_token=ACCESS,
                )
        assert len(transport.requests) == 1
    finally:
        await http.close()


@pytest.mark.parametrize(
    "header",
    [
        {"jku": "http://127.0.0.1/secret"},
        {"x5u": "https://evil.example/key"},
        {"kid": ""},
        {"kid": "x" * 257},
    ],
)
async def test_untrusted_header_cannot_choose_network(key, header):
    claims = {"sub": "x"}
    encoded = jwt.encode({"alg": "RS256", "kid": key.kid, **header}, claims, key)
    transport = RecordingTransport([])
    http = AuthHttpClient(settings(), transport=transport)
    try:
        with pytest.raises(AuthException):
            await OidcVerifier(http, settings()).verify(
                encoded, META, "client-a", FLOW.nonce, access_token=ACCESS
            )
        assert not transport.requests
    finally:
        await http.close()


async def test_discovery_must_match_configured_endpoints(key):
    meta = OidcMetadata(
        META.issuer,
        META.jwks_uri,
        META.algorithms,
        META.authorization_endpoint,
        META.token_endpoint,
        "https://issuer.example/.well-known/openid-configuration",
    )
    transport = RecordingTransport(
        [
            {
                "issuer": meta.issuer,
                "jwks_uri": "http://127.0.0.1/internal",
                "authorization_endpoint": meta.authorization_endpoint,
                "token_endpoint": meta.token_endpoint,
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        ]
    )
    http = AuthHttpClient(settings(), transport=transport)
    try:
        with pytest.raises(AuthException):
            await OidcVerifier(http, settings()).verify(
                oidc_token(key, meta, FLOW.nonce), meta, "client-a", FLOW.nonce, access_token=ACCESS
            )
        assert len(transport.requests) == 1 and transport.requests[0].url.host == "issuer.example"
    finally:
        await http.close()


async def test_refresh_id_token_nonce_optional_but_subject_stable(key):
    http = AuthHttpClient(
        settings(), transport=RecordingTransport([{"keys": [key.as_dict(private=False)]}])
    )
    verifier = OidcVerifier(http, settings())
    try:
        previous = await verifier.verify(
            oidc_token(key, META, FLOW.nonce), META, "client-a", FLOW.nonce, access_token=ACCESS
        )
        next_claims = {k: v for k, v in previous.items() if k != "nonce"}
        encoded = jwt.encode({"alg": "RS256", "kid": key.kid}, next_claims, key)
        assert (
            await verifier.verify(
                encoded,
                META,
                "client-a",
                FLOW.nonce,
                access_token=ACCESS,
                expected_subject=previous["sub"],
                previous_claims=previous,
            )
        )["sub"] == previous["sub"]
        with pytest.raises(AuthException):
            await verifier.verify(
                oidc_token(key, META, FLOW.nonce, sub="other"),
                META,
                "client-a",
                FLOW.nonce,
                access_token=ACCESS,
                expected_subject=previous["sub"],
                previous_claims=previous,
            )
    finally:
        await http.close()


@pytest.mark.parametrize("algorithms", [("none",), ("HS256",), ()])
def test_oidc_configuration_cannot_disable_signature_verification(algorithms):
    with pytest.raises(ValueError):
        OidcMetadata(
            META.issuer, META.jwks_uri, algorithms, META.authorization_endpoint, META.token_endpoint
        )


async def test_numeric_date_accepts_fractional_seconds(key):
    transport = RecordingTransport([{"keys": [key.as_dict(private=False)]}])
    http = AuthHttpClient(settings(), transport=transport)
    try:
        now = time.time()
        encoded = oidc_token(key, META, FLOW.nonce, iat=now, exp=now + 600.125, nbf=now - 0.5)
        claims = await OidcVerifier(http, settings()).verify(
            encoded, META, "client-a", FLOW.nonce, access_token=ACCESS
        )
        assert claims["iat"] == now and claims["exp"] == now + 600.125
    finally:
        await http.close()
