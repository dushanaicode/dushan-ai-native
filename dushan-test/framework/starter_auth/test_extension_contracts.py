import pytest

from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider

from .support import ACCESS, BINDING, REFRESH, client_config, provider_case


@pytest.mark.parametrize(
    "ids, subject, kind",
    [
        ({"taobao_user_id": "old-id", "taobao_open_uid": "new-id"}, "old-id", "taobao_user_id"),
        ({"taobao_open_uid": "new-id"}, "new-id", "taobao_open_uid"),
    ],
)
async def test_taobao_raw_identity_and_legacy_precedence(ids, subject, kind):
    provider, _, http = await provider_case("TAOBAO", [])
    try:
        tokens = provider.token(
            {
                "access_token": ACCESS,
                "refresh_token": REFRESH,
                "expires_in": 600,
                "taobao_user_nick": "User",
                **ids,
            }
        )
        identity = await provider.userinfo(tokens)
        assert identity.subject == subject and identity.subject_type == kind
        assert tokens.subject == subject and tokens.subject_type == kind
        assert "access_token" not in tokens.data and "refresh_token" not in tokens.data
    finally:
        await http.close()


@pytest.mark.parametrize("mode", ["wrong_kind", "foreign_binding"])
async def test_provider_output_contract_is_enforced(harness, mode):
    build, _, _ = harness

    class Extension(OAuthProvider):
        capabilities = (
            ProviderCapability(
                "EXT_VALIDATION",
                token_kind="session_key" if mode == "wrong_kind" else "access_token",
            ),
        )
        authorization_endpoint = "https://issuer.example/authorize"
        token_endpoint = "https://issuer.example/token"

        async def exchange(self, code, flow):
            token = self.tokens(access_token=ACCESS)
            return (
                token
                if mode == "wrong_kind"
                else token.model_copy(update={"client_id": "foreign-client"})
            )

        async def userinfo(self, tokens):
            pytest.fail("无效的 Provider 结果不得继续规范化身份")

    config = client_config().model_copy(update={"source": "EXT_VALIDATION", "pkce": False})
    service = await build(configs=(config,), components=(Extension,))
    request = await service.begin("app-a", config.source, binding=BINDING)
    with pytest.raises(AuthException) as failure:
        await service.complete(
            "app-a", config.source, [("state", request.state), ("code", "code")], binding=BINDING
        )
    assert failure.value.error_code == (Codes.RESPONSE if mode == "wrong_kind" else Codes.BINDING)
    assert failure.value.outcome == "unknown"


async def test_override_cannot_return_insecure_authorization_url(harness):
    build, _, cache = harness

    class Extension(OAuthProvider):
        capabilities = (ProviderCapability("EXT_URL"),)
        authorization_endpoint = "https://issuer.example/authorize"

        def authorize(self, flow, challenge):
            return "http://issuer.example/insecure?state=" + flow.state

    config = client_config().model_copy(update={"source": "EXT_URL", "pkce": False})
    service = await build(configs=(config,), components=(Extension,))
    with pytest.raises(AuthException) as failure:
        await service.begin("app-a", config.source, binding=BINDING)
    assert failure.value.error_code == Codes.CONFIG and service._http is None
    client = cache.get_client(service.store.key)
    assert not [
        key
        async for key in client.scan_iter(match="auth:state:" + service.settings.namespace + ":*")
    ]


def test_loopback_registration_requires_explicit_policy():
    class Extension(OAuthProvider):
        capabilities = (ProviderCapability("LOCAL_CONFIG"),)
        authorization_endpoint = "http://127.0.0.1:1234/authorize"

    with pytest.raises(AuthException):
        AuthProviderRegistry().register(Extension)
    AuthProviderRegistry().register(Extension, allow_loopback_http=True)
