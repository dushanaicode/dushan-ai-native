import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_result import AuthResult
from framework.starter_auth.provider.provider_payload import ProviderPayload

from .support import (
    ACCESS,
    CHANNEL_RESPONSES,
    EXPECTED_TOKEN_REQUEST,
    FLOW,
    REFRESH,
    SECRET,
    body,
    oidc_token,
    provider_case,
    rsa_key,
    settings,
)


@pytest.mark.parametrize("source", CHANNEL_RESPONSES)
async def test_channel_exchange_and_normalization(source):
    provider, transport, http = await provider_case(source, CHANNEL_RESPONSES[source])
    try:
        provider.validate_client(provider.config, settings())
        tokens = await provider.exchange("code+with/=symbols", FLOW)
        identity = await provider.userinfo(tokens)
        expected = "csdn-user" if source == "CSDN" else "123"
        assert identity.subject == expected
        assert identity.application_id == "app-a" and identity.source == source
        assert identity.client_id == "client-a" and identity.subject_type
        assert not transport.responses
        result = AuthResult(identity=identity, tokens=tokens)
        for secret in (SECRET, ACCESS, REFRESH, "session-key-secret"):
            assert (
                secret
                not in repr(result)
                + result.model_dump_json()
                + repr(tokens)
                + tokens.model_dump_json()
            )
        if source in EXPECTED_TOKEN_REQUEST:
            method, host, path, location, client_name, code_name = EXPECTED_TOKEN_REQUEST[source]
            request = transport.requests[0]
            assert (request.method, request.url.host, request.url.path) == (method, host, path)
            params = dict(request.url.params) if location == "query" else body(request)
            assert params[client_name] == "client-a"
            assert params[code_name] == "code+with/=symbols"
            if source in ("GITHUB", "FEISHU"):
                assert params["code_verifier"] == FLOW.verifier
        if source in ("DINGTALK", "DINGTALK_ACCOUNT"):
            request = transport.requests[0]
            params = dict(request.url.params)
            assert request.url.path == "/sns/getuserinfo_bycode"
            signature = base64.b64encode(
                hmac.new(SECRET.encode(), params["timestamp"].encode(), hashlib.sha256).digest()
            ).decode()
            assert params["signature"] == signature
            assert body(request) == {"tmp_auth_code": "code+with/=symbols"}
        if source.startswith("WECHAT_ENTERPRISE"):
            assert dict(transport.requests[0].url.params) == {
                "corpid": "client-a",
                "corpsecret": SECRET,
            }
            assert dict(transport.requests[1].url.params)["code"] == "code+with/=symbols"
            assert tokens.access_token is None
        if source.endswith("MINI_PROGRAM"):
            assert tokens.session_key.get_secret_value() == "session-key-secret"
            assert tokens.access_token is None and identity.nickname is None
        if source == "WECHAT_MP":
            assert identity.snapshot_user and identity.nickname is None
        if source == "ELEME":
            assert transport.requests[0].headers["Authorization"].startswith("Basic ")
            payload = body(transport.requests[1])
            assert 1_700_000_000 < payload["metas"]["timestamp"] < 10_000_000_000
            assert payload["action"] == "eleme.user.getUser"
        if source == "JD":
            params = body(transport.requests[1])
            assert json.loads(params["360buy_param_json"]) == {"openId": "123"}
            assert params["method"] == "jingdong.user.getUserInfoByOpenId"
            sign = params.pop("sign")
            canonical = SECRET + "".join(k + v for k, v in sorted(params.items())) + SECRET
            assert sign == hashlib.md5(canonical.encode()).hexdigest().upper()
    finally:
        await http.close()
    assert transport.closed


@pytest.mark.parametrize("source", CHANNEL_RESPONSES)
async def test_channel_authorization_and_unsupported(source):
    provider, _, http = await provider_case(source, [])
    try:
        if provider.capability.mode == "native":
            with pytest.raises(AuthException) as failure:
                provider.authorize(FLOW, "challenge")
            assert failure.value.error_code == Codes.UNSUPPORTED
        else:
            parsed = urlsplit(provider.authorize(FLOW, "challenge"))
            params = parse_qs(parsed.query, keep_blank_values=True)
            assert params["state"] == [FLOW.state]
            assert params["redirect_uri"] == [provider.config.redirect_uri]
            assert SECRET not in parsed.query
            if provider.capability.pkce:
                assert params["code_challenge_method"] == ["S256"]
            if source == "WECHAT_ENTERPRISE_CORP_APP":
                assert params["login_type"] == ["CorpApp"]
            if source == "WECHAT_ENTERPRISE_WEB":
                assert params["scope"] == ["snsapi_base"]
        tokens = provider.tokens()
        for operation in ("refresh", "revoke"):
            if not getattr(provider.capability, operation):
                with pytest.raises(AuthException) as failure:
                    await getattr(provider, operation)(tokens)
                assert failure.value.error_code == Codes.UNSUPPORTED
    finally:
        await http.close()


@pytest.mark.parametrize("source", CHANNEL_RESPONSES)
async def test_channel_malformed_token_never_succeeds(source):
    provider, transport, http = await provider_case(
        source, [{"error": ACCESS, "error_description": SECRET}]
    )
    try:
        with pytest.raises(AuthException) as failure:
            await provider.exchange("secret-code", FLOW)
        assert not failure.value.retryable
        assert ACCESS not in str(failure.value) and SECRET not in str(failure.value)
        assert len(transport.requests) == 1
    finally:
        await http.close()


@pytest.mark.parametrize("source", ["ALIYUN", "HUAWEI_V3"])
async def test_oidc_channel_contract(source):
    cls = AuthProviderRegistry().get(source)
    key = rsa_key()
    encoded = oidc_token(key, cls.oidc_metadata, FLOW.nonce)
    responses = [
        {"access_token": ACCESS, "refresh_token": REFRESH, "id_token": encoded, "expires_in": 600},
        {"keys": [key.as_dict(private=False)]},
    ]
    if source == "ALIYUN":
        responses.append({"sub": "external-subject", "login_name": "ali-user"})
    provider, transport, http = await provider_case(source, responses)
    try:
        provider.validate_client(provider.config, settings())
        tokens = await provider.exchange("code", FLOW)
        identity = await provider.userinfo(tokens)
        assert (
            identity.subject == "external-subject" and identity.issuer == cls.oidc_metadata.issuer
        )
        assert tokens.nonce == FLOW.nonce and tokens.claims["sub"] == identity.subject
        params = parse_qs(urlsplit(provider.authorize(FLOW, "challenge")).query)
        assert params["nonce"] == [FLOW.nonce]
        if source == "HUAWEI_V3":
            assert body(transport.requests[0])["code_verifier"] == FLOW.verifier
        assert not transport.responses
    finally:
        await http.close()


@pytest.mark.parametrize(
    "source", [s for s in CHANNEL_RESPONSES if AuthProviderRegistry().capability(s).refresh]
)
async def test_refresh_channel_contract(source):
    responses = CHANNEL_RESPONSES[source]
    provider, transport, http = await provider_case(source, [*responses, responses[0]])
    try:
        tokens = await provider.exchange("code", FLOW)
        identity = await provider.userinfo(tokens)
        tokens = tokens.model_copy(update={"subject": identity.subject})
        refreshed = await provider.refresh(tokens)
        assert refreshed.access_token.get_secret_value() == ACCESS
        request = transport.requests[-1]
        params = dict(request.url.params) if request.method == "GET" else body(request)
        assert params.get("grant_type", params.get("grantType")) == "refresh_token"
        assert params.get("refresh_token", params.get("refreshToken")) == REFRESH
        assert "code" not in params
        assert not transport.responses
    finally:
        await http.close()


@pytest.mark.parametrize(
    "source, response, success",
    [
        ("BAIDU", {"result": 1}, True),
        ("BAIDU", {"result": 0}, False),
        ("WEIBO", {"result": "true"}, True),
        ("WEIBO", {"result": True}, False),
        ("WEIBO", {"result": "false"}, False),
    ],
)
async def test_revoke_requires_explicit_success(source, response, success):
    provider, transport, http = await provider_case(source, [response])
    try:
        tokens = provider.tokens(access_token=ACCESS)
        if success:
            assert await provider.revoke(tokens) is None
        else:
            with pytest.raises(AuthException):
                await provider.revoke(tokens)
        assert len(transport.requests) == 1
    finally:
        await http.close()


@pytest.mark.parametrize("value", [True, {}, [], 1.2, None, ""])
def test_identifier_boundary(value):
    with pytest.raises(AuthException):
        ProviderPayload.identifier({"id": value}, "id")
