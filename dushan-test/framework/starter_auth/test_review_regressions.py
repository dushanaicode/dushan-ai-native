import httpx
import pytest
from pydantic import SecretStr
from starlette.datastructures import QueryParams

from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_callback import AuthCallback
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider

from .support import ACCESS, BINDING, REFRESH, RecordingTransport, client_config


def held_tokens(service, config, **values):
    provider = service.registry.get(config.source)(config, None, service.credentials, None)
    return provider.tokens(access_token=ACCESS, refresh_token=REFRESH, subject="123", **values)


@pytest.mark.parametrize(
    "source,response",
    [
        ("WECHAT_OPEN", {"access_token": ACCESS, "expires_in": 600, "openid": "other"}),
        ("WECHAT_MP", {"access_token": ACCESS, "expires_in": 600, "openid": "other"}),
        ("DOUYIN", {"data": {"access_token": ACCESS, "expires_in": 600, "open_id": "other"}}),
        ("MI", '{"access_token":"' + ACCESS + '","expires_in":600,"openId":"other"}'),
    ],
)
async def test_changed_refresh_identity_is_unknown(harness, source, response):
    build, _, _ = harness
    config = client_config(source)
    transport = RecordingTransport([response])
    service = await build(configs=(config,), transport=transport)
    with pytest.raises(AuthException) as failure:
        await service.refresh(held_tokens(service, config))
    assert failure.value.error_code == Codes.BINDING
    assert failure.value.outcome == "unknown"
    assert len(transport.requests) == 1


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("sensitive-cause"), {"userid": "other"}])
async def test_enterprise_failure_after_code_is_unknown(harness, failure):
    build, _, _ = harness
    config = client_config("WECHAT_ENTERPRISE")
    transport = RecordingTransport(
        [
            {"access_token": ACCESS, "expires_in": 7200},
            {"UserId": "123"},
            failure,
        ]
    )
    service = await build(configs=(config,), transport=transport)
    request = await service.begin("app-a", config.source, binding=BINDING)
    with pytest.raises(AuthException) as error:
        await service.complete(
            "app-a", config.source, [("state", request.state), ("code", "code")], binding=BINDING
        )
    assert error.value.outcome == "unknown"
    assert len(transport.requests) == 3


async def test_secret_rotation_preserves_refresh_but_invalidates_pending_state(harness):
    build, _, _ = harness
    config = client_config()
    transport = RecordingTransport([{"access_token": "new-access", "refresh_token": "new-refresh"}])
    service = await build(configs=(config,), transport=transport)
    tokens = held_tokens(service, config)
    pending = await service.begin("app-a", config.source, binding=BINDING)
    replacement = config.model_copy(
        update={
            "revision": 2,
            "client_secret": SecretStr("rotated-secret"),
            "scopes": ("read:user",),
            "redirect_uri": "https://app.example/new-callback",
        }
    )
    service.clients._clients[("app-a", config.source)] = replacement
    refreshed = await service.refresh(tokens)
    assert refreshed.refresh_token.get_secret_value() == "new-refresh"
    assert b"client_secret=rotated-secret" in transport.requests[0].content
    with pytest.raises(AuthException) as failure:
        await service.complete(
            "app-a", config.source, [("state", pending.state), ("code", "code")], binding=BINDING
        )
    assert failure.value.error_code == Codes.STATE and len(transport.requests) == 1


@pytest.mark.parametrize(
    "value",
    [
        {"state": "state", "code": "code"},
        QueryParams("state=state&code=code"),
        ["ab", "cd"],
        [None],
    ],
)
def test_wrong_callback_container_is_input_error(value):
    with pytest.raises(AuthException) as failure:
        AuthCallback.parse(value, code_parameter="code", client_id="client-a")
    assert failure.value.error_code == Codes.INPUT


@pytest.mark.parametrize(
    "source,url",
    [("lower_case", "https://issuer.example/auth"), ("EXT_HTTP", "http://issuer.example/auth")],
)
def test_registration_rejects_unusable_identity_and_insecure_url(source, url):
    class Extension(OAuthProvider):
        capabilities = (ProviderCapability(source),)
        authorization_endpoint = url

    with pytest.raises(AuthException) as failure:
        AuthProviderRegistry().register(Extension)
    assert failure.value.error_code == Codes.CONFIG
