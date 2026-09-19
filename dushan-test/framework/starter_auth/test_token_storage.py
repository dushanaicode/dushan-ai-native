import json

import pytest
from joserfc import jwt
from pydantic import SecretStr

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_tokens import AuthTokens

from .support import (
    ACCESS,
    FLOW,
    REFRESH,
    SECRET,
    RecordingTransport,
    client_config,
    oidc_token,
    rsa_key,
)
from .test_review_regressions import held_tokens


def test_explicit_storage_roundtrip_keeps_secrets_hidden_by_default():
    tokens = AuthTokens(
        application_id="app-a",
        source="HUAWEI_V3",
        client_id="client-a",
        subject="subject",
        subject_type="sub",
        access_token=ACCESS,
        refresh_token=REFRESH,
        id_token="signed-id-token",
        nonce="original-nonce",
        claims={"sub": "subject", "auth_time": 12345, "aud": "client-a", "iss": "issuer"},
        data={"metadata": {"access_token": ACCESS, "refresh_token": REFRESH}, "name": "User"},
    )
    stored = tokens.to_storage_json()
    assert isinstance(stored, SecretStr)
    assert ACCESS not in repr(stored) + str(stored) + repr(tokens) + tokens.model_dump_json()
    assert "fingerprint" not in json.loads(stored.get_secret_value())
    restored = AuthTokens.from_storage_json(stored.get_secret_value())
    assert restored == tokens
    assert restored.claims["auth_time"] == 12345
    assert restored.data == {"metadata": {}, "name": "User"}
    assert restored.refresh_token.get_secret_value() == REFRESH


def test_corrupt_storage_error_does_not_expose_record():
    with pytest.raises(AuthException) as error:
        AuthTokens.from_storage_json('{"refresh_token":"' + SECRET + '","source":42}')
    assert error.value.error_code == Codes.INPUT
    safe = SafeExceptionDiagnostics.snapshot(error.value)
    assert SECRET not in str(safe) + repr(safe.__dict__)


@pytest.mark.parametrize("source", ["ALIYUN", "HUAWEI_V3"])
@pytest.mark.parametrize("saved_claims", [True, False])
async def test_restored_oidc_refresh_without_nonce_keeps_subject(harness, source, saved_claims):
    build, _, _ = harness
    config = client_config(source)
    service = await build(configs=(config,))
    cls = service.registry.get(source)
    key = rsa_key()
    original = {
        "iss": cls.oidc_metadata.issuer,
        "aud": "client-a",
        "sub": "123",
        "auth_time": 100.5,
        "nonce": FLOW.nonce,
    }
    tokens = held_tokens(
        service,
        config,
        subject_type="sub",
        claims=original if saved_claims else None,
        nonce=FLOW.nonce if saved_claims else None,
    )
    restored = AuthTokens.from_storage_json(tokens.to_storage_json().get_secret_value())
    import time

    claims = {
        "iss": cls.oidc_metadata.issuer,
        "aud": "client-a",
        "sub": "123",
        "iat": time.time(),
        "exp": time.time() + 600,
    }
    if saved_claims:
        claims["auth_time"] = 100.5
    encoded = jwt.encode({"alg": "RS256", "kid": key.kid}, claims, key)
    transport = RecordingTransport(
        [
            {"access_token": "new-access", "expires_in": 600, "id_token": encoded},
            {"keys": [key.as_dict(private=False)]},
        ]
    )
    service._transport = transport
    refreshed = await service.refresh(restored)
    assert refreshed.subject == "123" and refreshed.subject_type == "sub"
    assert refreshed.claims["sub"] == "123"
    assert refreshed.refresh_token == restored.refresh_token
    assert refreshed.nonce == restored.nonce
    assert len(transport.requests) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"sub": "other"},
        {"nonce": "wrong"},
        {"aud": ["client-a", "extra"], "azp": "client-a"},
        {"auth_time": 11.5},
    ],
)
async def test_restored_oidc_refresh_rejects_changed_binding(harness, change):
    build, _, _ = harness
    config = client_config("HUAWEI_V3")
    service = await build(configs=(config,))
    cls = service.registry.get(config.source)
    key = rsa_key()
    previous = {"iss": cls.oidc_metadata.issuer, "aud": "client-a", "sub": "123", "auth_time": 10.5}
    tokens = held_tokens(service, config, claims=previous, nonce=FLOW.nonce, subject_type="sub")
    tokens = AuthTokens.from_storage_json(tokens.to_storage_json().get_secret_value())
    values = {"sub": "123", "auth_time": 10.5, **change}
    encoded = oidc_token(key, cls.oidc_metadata, FLOW.nonce, **values)
    service._transport = RecordingTransport(
        [
            {"access_token": ACCESS, "expires_in": 600, "id_token": encoded},
            {"keys": [key.as_dict(private=False)]},
        ]
    )
    with pytest.raises(AuthException) as failure:
        await service.refresh(tokens)
    assert failure.value.error_code == Codes.OIDC and failure.value.outcome == "unknown"


async def test_stable_client_binding_rejects_different_client_before_http(harness):
    build, _, _ = harness
    config = client_config()
    transport = RecordingTransport([])
    service = await build(configs=(config,), transport=transport)
    tokens = held_tokens(service, config).model_copy(update={"client_id": "other-client"})
    for operation in (service.refresh, service.userinfo):
        with pytest.raises(AuthException) as failure:
            await operation(tokens)
        assert failure.value.error_code == Codes.BINDING
    assert not transport.requests and service._http is None


async def test_stored_token_can_revoke_after_configuration_rotation(harness):
    build, _, _ = harness
    config = client_config("WEIBO")
    transport = RecordingTransport([{"result": "true"}])
    service = await build(configs=(config,), transport=transport)
    tokens = AuthTokens.from_storage_json(
        held_tokens(service, config).to_storage_json().get_secret_value()
    )
    service.clients._clients[(config.application_id, config.source)] = config.model_copy(
        update={
            "client_secret": SecretStr("new-secret"),
            "revision": 2,
            "redirect_uri": "https://app.example/changed",
        }
    )
    await service.revoke(tokens)
    assert len(transport.requests) == 1
