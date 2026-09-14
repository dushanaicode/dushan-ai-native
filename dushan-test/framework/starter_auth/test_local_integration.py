from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from framework.starter_auth.core.auth_http_client import AuthHttpClient
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_tokens import AuthTokens
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.oauth_provider import OAuthProvider

from .local_authorization_server import LocalAuthorizationServer
from .support import BINDING, client_config, settings


@pytest.fixture
async def authorization_server():
    server = await LocalAuthorizationServer().open()
    try:
        yield server
    finally:
        await server.close()
    assert server.closed and not server._tasks and not server.server.is_serving()


def local_provider(server):
    class LocalProvider(OAuthProvider):
        capabilities = (
            ProviderCapability("LOCAL_OIDC", oidc=True, pkce=True, refresh=True, revoke=True),
        )
        authorization_endpoint = server.origin + "/authorize"
        token_endpoint = server.origin + "/token"
        userinfo_endpoint = server.origin + "/user"
        subject_field = "sub"
        profile_fields = {"nickname": "name"}
        oidc_metadata = OidcMetadata(
            server.origin,
            server.origin + "/keys",
            ("RS256",),
            authorization_endpoint,
            token_endpoint,
            server.origin + "/.well-known/openid-configuration",
        )

        async def revoke(self, tokens):
            await self.http.json(
                "POST", server.origin + "/revoke", effect=True, data={"token": self.access(tokens)}
            )

    return LocalProvider


async def test_real_http_redis_oidc_full_flow(authorization_server, harness):
    build, _, _ = harness
    cls = local_provider(authorization_server)
    config = client_config().model_copy(
        update={
            "source": "LOCAL_OIDC",
            "scopes": ("openid",),
            "redirect_uri": "http://127.0.0.1/callback",
        }
    )
    service = await build(configs=(config,), components=(cls,))
    initial = await service.begin("app-a", "LOCAL_OIDC", binding=BINDING)
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as browser:
        page = await browser.get(initial.url)
    assert page.status_code == 302
    callback = parse_qsl(urlsplit(page.headers["location"]).query)
    result = await service.complete("app-a", "LOCAL_OIDC", callback, binding=BINDING)
    assert result.identity.subject == "local-subject" and result.identity.nickname == "Local User"
    assert result.tokens.claims["iss"] == authorization_server.origin
    persisted = result.tokens.to_storage_json().get_secret_value()
    authorization_server.client_secret = "rotated-local-secret"
    service.clients._clients[("app-a", "LOCAL_OIDC")] = config.model_copy(
        update={
            "client_secret": SecretStr("rotated-local-secret"),
            "revision": 2,
            "redirect_uri": "http://127.0.0.1/new-callback",
        }
    )
    renewed = await service.refresh(AuthTokens.from_storage_json(persisted))
    assert renewed.access_token != result.tokens.access_token
    assert (await service.userinfo(renewed)).subject == result.identity.subject
    with pytest.raises(AuthException):
        await service.refresh(result.tokens)
    await service.revoke(renewed)
    with pytest.raises(AuthException):
        await service.userinfo(renewed)
    with pytest.raises(AuthException):
        await service.complete("app-a", "LOCAL_OIDC", callback, binding=BINDING)
    assert authorization_server.calls.count(("GET", "/keys")) == 1
    assert authorization_server.calls.count(("GET", "/.well-known/openid-configuration")) == 1
    assert authorization_server.calls.count(("POST", "/token")) == 3
    await service.close()
    assert service._http.client.is_closed


async def test_local_server_rejects_wrong_pkce():
    server = await LocalAuthorizationServer().open()
    try:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as browser:
            page = await browser.get(
                server.origin + "/authorize",
                params={
                    "code_challenge_method": "S256",
                    "code_challenge": "correct",
                    "state": "state",
                    "nonce": "nonce",
                    "redirect_uri": "https://app.example/callback",
                },
            )
            code = dict(parse_qsl(urlsplit(page.headers["location"]).query))["code"]
            from .support import SECRET

            response = await browser.post(
                server.origin + "/token",
                data={
                    "client_id": "client-a",
                    "client_secret": SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "https://app.example/callback",
                    "code_verifier": "wrong",
                },
            )
            assert response.status_code == 400
            assert response.json()["error"] == "invalid_grant"
    finally:
        await server.close()


async def test_real_http_timeout_and_response_limit(authorization_server):
    server = authorization_server
    http = AuthHttpClient(settings(http_timeout_seconds=0.03, max_response_bytes=1024))
    try:
        with pytest.raises(AuthException) as failure:
            await http.json("POST", server.origin + "/slow", effect=True)
        assert failure.value.outcome == "unknown"
        with pytest.raises(AuthException):
            await http.json("GET", server.origin + "/oversize")
        assert server.calls.count(("POST", "/slow")) == 1
    finally:
        server.release_slow.set()
        await http.close()


async def test_real_http_nonce_mismatch(authorization_server, harness):
    build, _, _ = harness
    cls = local_provider(authorization_server)
    config = client_config().model_copy(
        update={
            "source": "LOCAL_OIDC",
            "scopes": ("openid",),
            "redirect_uri": "http://127.0.0.1/callback",
        }
    )
    service = await build(configs=(config,), components=(cls,))
    request = await service.begin("app-a", "LOCAL_OIDC", binding=BINDING)
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as browser:
        response = await browser.get(request.url)
    authorization_server.nonce_override = "wrong-nonce"
    with pytest.raises(AuthException):
        await service.complete(
            "app-a",
            "LOCAL_OIDC",
            parse_qsl(urlsplit(response.headers["location"]).query),
            binding=BINDING,
        )
    assert ("GET", "/user") not in authorization_server.calls
