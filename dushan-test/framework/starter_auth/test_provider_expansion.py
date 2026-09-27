import base64
import json
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from joserfc import jwt

from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.provider.apple_provider import AppleProvider

from .support import ACCESS, FLOW, client_config, oidc_token, provider_case, rsa_key, settings

TENANT_GUID = "72f988bf-86f1-41af-91ab-2d7cd011db47"


def discovery(metadata):
    """按渠道元数据构造与官方 discovery 同形的响应。"""
    return {
        "issuer": metadata.issuer,
        "jwks_uri": metadata.jwks_uri,
        "authorization_endpoint": metadata.authorization_endpoint,
        "token_endpoint": metadata.token_endpoint,
        "id_token_signing_alg_values_supported": list(metadata.algorithms),
    }


def test_first_party_provider_expansion_is_registered():
    registry = AuthProviderRegistry()
    assert {
        "GOOGLE",
        "MICROSOFT",
        "APPLE",
        "GITHUB",
        "GITLAB",
        "DISCORD",
        "SLACK",
        "LINKEDIN",
    }.issubset({capability.source for capability in registry.capabilities()})


def test_standard_oidc_metadata_is_discoverable():
    registry = AuthProviderRegistry()
    for source in ("GOOGLE", "SLACK", "LINKEDIN"):
        metadata = registry.get(source).oidc_metadata
        assert metadata.discovery_uri and metadata.jwks_uri and metadata.issuer


def test_microsoft_uses_tenant_guid_for_single_tenant_endpoints():
    config = client_config(
        "MICROSOFT", scopes=("openid",), pkce=True, options={"tenant": TENANT_GUID}
    )
    provider = AuthProviderRegistry().get("MICROSOFT")(config, None, None, None)
    metadata = provider.oidc_metadata_for_config()
    base = "https://login.microsoftonline.com/" + TENANT_GUID
    assert provider.authorization_endpoint == base + "/oauth2/v2.0/authorize"
    assert provider.token_endpoint == base + "/oauth2/v2.0/token"
    assert metadata.issuer == base + "/v2.0" and metadata.issuer_pattern is None
    assert metadata.jwks_uri == base + "/discovery/v2.0/keys"


@pytest.mark.parametrize("tenant", ["contoso.onmicrosoft.com", "common.evil", "tenant-123"])
def test_microsoft_rejects_tenants_without_guid_issuer(tenant):
    """域名形式的租户仍然签发 GUID issuer，配置阶段就要拒绝，避免登录期才失败。"""
    config = client_config("MICROSOFT", scopes=("openid",), pkce=True, options={"tenant": tenant})
    with pytest.raises(AuthException):
        AuthProviderRegistry().get("MICROSOFT").validate_client(config, settings())


@pytest.mark.parametrize("tenant", ["common", "organizations", "consumers"])
def test_microsoft_shared_tenants_keep_issuer_pattern(tenant):
    config = client_config("MICROSOFT", scopes=("openid",), pkce=True, options={"tenant": tenant})
    provider = AuthProviderRegistry().get("MICROSOFT")(config, None, None, None)
    assert provider.oidc_metadata_for_config().issuer_pattern is not None


def test_gitlab_supports_self_managed_base_url():
    config = client_config(
        "GITLAB",
        scopes=("read_user",),
        pkce=True,
        options={"base_url": "https://gitlab.example.test"},
    )
    provider = AuthProviderRegistry().get("GITLAB")(config, None, None, None)
    assert provider.authorization_endpoint == "https://gitlab.example.test/oauth/authorize"
    assert provider.token_endpoint == "https://gitlab.example.test/oauth/token"
    assert provider.userinfo_endpoint == "https://gitlab.example.test/api/v4/user"
    assert provider.capability.refresh_rotation


def test_apple_client_secret_is_es256_jwt():
    key = ec.generate_private_key(ec.SECP256R1())
    private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    config = client_config(
        "APPLE",
        client_secret=private_key,
        scopes=("openid", "email"),
        options={"team_id": "TEAM123", "key_id": "KEY123"},
    )
    token = AppleProvider._client_secret(config)
    encoded_header, encoded_claims, encoded_signature = token.split(".")

    def decode(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    header = json.loads(decode(encoded_header))
    claims = json.loads(decode(encoded_claims))
    assert header == {"alg": "ES256", "kid": "KEY123", "typ": "JWT"}
    assert claims["iss"] == "TEAM123" and claims["sub"] == "client-a"
    assert claims["aud"] == "https://appleid.apple.com"
    assert claims["exp"] - claims["iat"] <= 15_777_000
    assert len(decode(encoded_signature)) == 64


async def test_google_requests_offline_access_for_refresh_token():
    provider, _, http = await provider_case("GOOGLE", [])
    try:
        params = parse_qs(urlsplit(provider.authorize(FLOW, "challenge")).query)
        assert params["access_type"] == ["offline"] and provider.capability.refresh
    finally:
        await http.close()


@pytest.mark.parametrize(
    "scopes, expected", [(("openid",), None), (("openid", "email"), "form_post")]
)
async def test_apple_uses_form_post_only_when_name_or_email_requested(scopes, expected):
    config = client_config("APPLE", scopes=scopes, options={"team_id": "T", "key_id": "K"})
    provider, _, http = await provider_case("APPLE", [], config)
    try:
        params = parse_qs(urlsplit(provider.authorize(FLOW, "challenge")).query)
        assert params.get("response_mode", [None])[0] == expected
    finally:
        await http.close()


async def test_slack_token_response_without_expires_in_is_accepted():
    """openid.connect.token 不返回 expires_in，强制要求会让 Slack 登录必然失败。"""
    key = rsa_key()
    metadata = AuthProviderRegistry().get("SLACK").oidc_metadata
    config = client_config("SLACK", scopes=("openid", "profile", "email"))
    provider, transport, http = await provider_case(
        "SLACK",
        [
            {
                "ok": True,
                "access_token": ACCESS,
                "token_type": "Bearer",
                "id_token": oidc_token(key, metadata, FLOW.nonce),
            },
            discovery(metadata),
            {"keys": [key.as_dict(private=False)]},
        ],
        config,
    )
    try:
        tokens = await provider.exchange("code", FLOW)
        assert tokens.expires_in is None and tokens.subject == "external-subject"
        assert tokens.claims["nonce"] == FLOW.nonce and not transport.responses
    finally:
        await http.close()


async def test_linkedin_id_token_without_nonce_and_bare_issuer_is_accepted():
    """LinkedIn 不回传 nonce，且签发的 iss 与 discovery 声明的取值不一致。"""
    key = rsa_key()
    metadata = AuthProviderRegistry().get("LINKEDIN").oidc_metadata
    now = int(time.time())
    encoded = jwt.encode(
        {"alg": "RS256", "kid": key.kid},
        {
            "iss": "https://www.linkedin.com",
            "aud": "client-a",
            "sub": "linkedin-member",
            "iat": now,
            "exp": now + 600,
        },
        key,
    )
    provider, transport, http = await provider_case(
        "LINKEDIN",
        [
            {"access_token": ACCESS, "expires_in": 5184000, "id_token": encoded},
            discovery(metadata),
            {"keys": [key.as_dict(private=False)]},
        ],
    )
    try:
        tokens = await provider.exchange("code", FLOW)
        assert tokens.subject == "linkedin-member" and "nonce" not in tokens.claims
        assert not transport.responses
    finally:
        await http.close()


async def test_oidc_channels_still_require_matching_nonce_when_returned():
    """放宽只针对未回传 nonce 的渠道；回传了就必须一致。"""
    key = rsa_key()
    metadata = AuthProviderRegistry().get("LINKEDIN").oidc_metadata
    provider, _, http = await provider_case(
        "LINKEDIN",
        [
            {
                "access_token": ACCESS,
                "expires_in": 5184000,
                "id_token": oidc_token(key, metadata, "other-nonce"),
            },
            discovery(metadata),
            {"keys": [key.as_dict(private=False)]},
        ],
    )
    try:
        with pytest.raises(AuthException):
            await provider.exchange("code", FLOW)
    finally:
        await http.close()


async def test_discord_avatar_hash_becomes_cdn_url():
    provider, _, http = await provider_case(
        "DISCORD", [{"id": "123", "username": "dusty", "avatar": "abc123", "email": None}]
    )
    try:
        identity = await provider.userinfo(provider.tokens(access_token=ACCESS))
        assert identity.avatar == "https://cdn.discordapp.com/avatars/123/abc123.png"
        assert identity.subject == "123" and identity.email is None
    finally:
        await http.close()
