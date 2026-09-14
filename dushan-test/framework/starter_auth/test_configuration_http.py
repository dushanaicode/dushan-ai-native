import logging

import httpx
import pytest
from pydantic import ValidationError

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.starter_auth.core.auth_http_client import AuthHttpClient
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider

from .support import ACCESS, SECRET, RecordingTransport, client_config, settings


def test_complete_registry_and_isolated_extension():
    first, second = AuthProviderRegistry(), AuthProviderRegistry()
    assert {cap.source for cap in first.capabilities()} == {
        "ALIPAY",
        "ALIPAY_CERT",
        "ALIYUN",
        "BAIDU",
        "CSDN",
        "DINGTALK",
        "DINGTALK_ACCOUNT",
        "DINGTALK_V2",
        "DOUYIN",
        "ELEME",
        "FEISHU",
        "GITEE",
        "GITHUB",
        "HUAWEI",
        "HUAWEI_V3",
        "JD",
        "MEITUAN",
        "MI",
        "QQ",
        "QQ_MINI_PROGRAM",
        "TAOBAO",
        "TOUTIAO",
        "WECHAT_ENTERPRISE",
        "WECHAT_ENTERPRISE_CORP_APP",
        "WECHAT_ENTERPRISE_WEB",
        "WECHAT_MINI_PROGRAM",
        "WECHAT_MP",
        "WECHAT_OPEN",
        "WEIBO",
    }

    class Custom(OAuthProvider):
        capabilities = (ProviderCapability("TEST_EXTENSION"),)

    first.register(Custom)
    assert first.get("TEST_EXTENSION") is Custom
    with pytest.raises(AuthException):
        second.get("TEST_EXTENSION")
    with pytest.raises(AuthException):
        first.register(Custom)
    first.seal()
    with pytest.raises(AuthException):
        first.register(Custom)


@pytest.mark.parametrize(
    "field", ["enabled", "namespace", "state_ttl_seconds", "http_timeout_seconds", "clients"]
)
def test_missing_configuration_is_not_defaulted(field):
    values = settings().model_dump()
    del values[field]
    with pytest.raises(ValidationError):
        type(settings())(**values)


def test_disabled_client_requires_no_credentials_and_secrets_not_exported():
    inactive = client_config(enabled=False, client_id=None, client_secret=None)
    assert not inactive.enabled
    with pytest.raises(ValidationError):
        client_config(client_secret=None)
    cfg = client_config()
    assert SECRET not in repr(cfg) + cfg.model_dump_json()
    assert cfg.fingerprint() != client_config(client_secret="another-secret").fingerprint()
    with pytest.raises(ValidationError):
        settings(clients=(cfg, cfg))


@pytest.mark.parametrize(
    "source, changes",
    [
        ("GITHUB", {"pkce": False}),
        ("GITEE", {"pkce": True}),
        ("WECHAT_OPEN", {"scopes": ("snsapi_base",)}),
        ("WECHAT_ENTERPRISE_WEB", {"options": {}}),
        ("WECHAT_MINI_PROGRAM", {"redirect_uri": "https://app.example/callback"}),
        ("HUAWEI_V3", {"scopes": ("profile",)}),
        ("GITHUB", {"options": {"token_endpoint": "https://evil.example"}}),
    ],
)
def test_channel_config_capability_validation(source, changes):
    cfg = client_config(source, **changes)
    with pytest.raises(AuthException):
        AuthProviderRegistry().get(source).validate_client(cfg, settings())


@pytest.mark.parametrize(
    "url",
    [
        "http://public.example/callback",
        "https://user:pass@host.test/callback",
        "https://host.test/#fragment",
        "https://host.test/\n",
        "https://host.test\\evil",
        "//host.test",
        "https://host.test:0/callback",
        "https://host%2Etest/callback",
    ],
)
def test_invalid_url_policy(url):
    with pytest.raises(AuthException):
        AuthUrlPolicy.require(url, allow_loopback_http=True)


def test_loopback_http_requires_explicit_policy():
    with pytest.raises(AuthException):
        AuthUrlPolicy.require("http://127.0.0.1:1234", allow_loopback_http=False)
    AuthUrlPolicy.require("http://127.0.0.1:1234", allow_loopback_http=True)


@pytest.mark.parametrize(
    "error, outcome",
    [
        (httpx.ConnectTimeout(SECRET), "not_sent"),
        (httpx.PoolTimeout(SECRET), "not_sent"),
        (httpx.ReadTimeout(SECRET), "unknown"),
        (httpx.WriteError(SECRET), "unknown"),
        (httpx.RemoteProtocolError(SECRET), "unknown"),
    ],
)
async def test_http_failure_semantics_no_retry(error, outcome):
    transport = RecordingTransport([error])
    http = AuthHttpClient(settings(), transport=transport)
    try:
        with pytest.raises(AuthException) as failure:
            await http.json(
                "POST", "https://issuer.example/token", effect=True, data={"code": SECRET}
            )
        assert failure.value.outcome == outcome and not failure.value.retryable
        assert len(transport.requests) == 1 and failure.value.__cause__ is error
        safe = SafeExceptionDiagnostics.snapshot(failure.value)
        assert SECRET not in str(safe) + repr(safe.__dict__)
    finally:
        await http.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://evil.example/"}),
        httpx.Response(500),
        httpx.Response(200, content=b"x" * 1025),
        httpx.Response(200, content=b"{}", headers={"content-encoding": "br"}),
        httpx.Response(200, content=b'{"access_token":"a","access_token":"b"}'),
    ],
)
async def test_transport_redirect_size_encoding_and_duplicate_json(response):
    transport = RecordingTransport([response])
    http = AuthHttpClient(settings(max_response_bytes=1024), transport=transport)
    try:
        with pytest.raises(AuthException):
            await http.json("POST", "https://issuer.example/token", effect=True)
        assert len(transport.requests) == 1
    finally:
        await http.close()


async def test_http_cookie_and_logging_isolation(caplog):
    caplog.set_level(logging.DEBUG, logger="httpx")
    transport = RecordingTransport(
        [
            httpx.Response(
                200, json={"ok": True}, headers={"Set-Cookie": "session=" + SECRET + "; Path=/"}
            ),
            {"ok": True},
        ]
    )
    http = AuthHttpClient(settings(), transport=transport)
    try:
        await http.json("GET", "https://issuer.example/token", params={"access_token": ACCESS})
        await http.json("GET", "https://issuer.example/user", params={"client_secret": SECRET})
        assert all("cookie" not in req.headers for req in transport.requests)
        assert not http.client.cookies
        assert ACCESS not in caplog.text and SECRET not in caplog.text
        logging.getLogger("httpx").info("unrelated HTTP client event")
        assert "unrelated HTTP client event" in caplog.text
    finally:
        await http.close()
