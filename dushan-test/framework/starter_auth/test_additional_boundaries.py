import asyncio
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider

from .support import (
    ACCESS,
    BINDING,
    CHANNEL_RESPONSES,
    FLOW,
    REFRESH,
    RecordingTransport,
    client_config,
    oidc_token,
    provider_case,
    rsa_key,
)


@pytest.mark.parametrize("source", ["WECHAT_MINI_PROGRAM", "QQ_MINI_PROGRAM"])
async def test_native_challenge_and_atomic_callback(harness, source):
    build, _, _ = harness
    transport = RecordingTransport(CHANNEL_RESPONSES[source])
    service = await build(configs=(client_config(source),), transport=transport)
    challenge = await service.begin("app-a", source, binding=BINDING)
    assert challenge.url is None
    result = await service.complete(
        "app-a", source, [("state", challenge.state), ("code", "native-code")], binding=BINDING
    )
    assert result.tokens.session_key is not None and result.tokens.access_token is None
    with pytest.raises(AuthException):
        await service.complete(
            "app-a", source, [("state", challenge.state), ("code", "native-code")], binding=BINDING
        )
    assert len(transport.requests) == 1


async def test_oidc_state_material_is_atomic_and_expires(harness):
    build, _, cache = harness
    # 不给真实 transport：过期判断如果被时钟抖动绕过，交换会在这里因为没有可用响应
    # 立即报错，而不是意外向厂商真实生产端点发出请求。
    service = await build(
        configs=(client_config("HUAWEI_V3"),),
        state_ttl_seconds=1,
        transport=RecordingTransport([]),
    )
    config = service.clients._clients[("app-a", "HUAWEI_V3")]
    challenge = await service.begin("app-a", "HUAWEI_V3", binding=BINDING)
    key = cache.build_full_key(service.store.key, service.store.identifier(config, challenge.state))
    redis = cache.get_client(service.store.key)
    payload = await redis.hgetall(key)
    assert set(payload) == {"binding", "client", "nonce", "verifier"}
    assert payload["nonce"] == parse_qs(urlsplit(challenge.url).query)["nonce"][0]
    assert 0 < await redis.pttl(key) <= 1000
    # 轮询真实过期而不是睡一个固定余量：真实系统时钟下固定 50ms 余量并不可靠。
    deadline = asyncio.get_event_loop().time() + 5
    while await redis.pttl(key) > 0:
        assert asyncio.get_event_loop().time() < deadline, "state key 未在预期时间内过期"
        await asyncio.sleep(0.02)
    with pytest.raises(AuthException) as failure:
        await service.complete(
            "app-a", "HUAWEI_V3", [("state", challenge.state), ("code", "code")], binding=BINDING
        )
    assert failure.value.error_code == Codes.STATE and service._http is None


async def test_missing_nonce_in_cache_cannot_start_exchange(harness):
    build, _, cache = harness
    service = await build(configs=(client_config("HUAWEI_V3"),))
    config = service.clients._clients[("app-a", "HUAWEI_V3")]
    challenge = await service.begin("app-a", "HUAWEI_V3", binding=BINDING)
    key = cache.build_full_key(service.store.key, service.store.identifier(config, challenge.state))
    await cache.get_client(service.store.key).hdel(key, "nonce")
    with pytest.raises(AuthException):
        await service.complete(
            "app-a", "HUAWEI_V3", [("state", challenge.state), ("code", "code")], binding=BINDING
        )
    assert service._http is None


async def test_huawei_v3_explicit_profile_keeps_oidc_subject():
    cls = AuthProviderRegistry().get("HUAWEI_V3")
    key = rsa_key()
    config = client_config(
        "HUAWEI_V3", scopes=("openid", "https://www.huawei.com/auth/account/base.profile")
    )
    responses = [
        {
            "access_token": ACCESS,
            "expires_in": 600,
            "id_token": oidc_token(key, cls.oidc_metadata, FLOW.nonce),
        },
        {"keys": [key.as_dict(private=False)]},
        {
            "unionID": "separate-union",
            "displayName": "Huawei profile",
            "headPictureURL": "https://avatar.example/pic",
        },
    ]
    provider, transport, http = await provider_case("HUAWEI_V3", responses, config)
    try:
        tokens = await provider.exchange("code", FLOW)
        user = await provider.userinfo(tokens)
        assert user.subject == "external-subject" and user.union_id == "separate-union"
        assert user.nickname == "Huawei profile"
        assert transport.requests[-1].url.host == "account.cloud.huawei.com"
    finally:
        await http.close()


async def test_wechat_mp_userinfo_scope_and_enterprise_detail():
    provider, transport, http = await provider_case(
        "WECHAT_MP",
        [
            {
                "access_token": ACCESS,
                "refresh_token": REFRESH,
                "expires_in": 600,
                "openid": "123",
                "scope": "snsapi_userinfo",
            },
            {"openid": "123", "nickname": "User", "unionid": "union"},
        ],
        client_config("WECHAT_MP", scopes=("snsapi_userinfo",)),
    )
    try:
        user = await provider.userinfo(await provider.exchange("code", FLOW))
        assert user.nickname == "User" and len(transport.requests) == 2
    finally:
        await http.close()
    provider, transport, http = await provider_case(
        "WECHAT_ENTERPRISE_WEB",
        [
            {"access_token": ACCESS, "expires_in": 7200},
            {"UserId": "123", "user_ticket": "ticket"},
            {"userid": "123", "name": "Name"},
            {"userid": "123", "email": "user@example.test"},
        ],
        client_config("WECHAT_ENTERPRISE_WEB", scopes=("snsapi_privateinfo",)),
    )
    try:
        user = await provider.userinfo(await provider.exchange("code", FLOW))
        assert user.email == "user@example.test" and len(transport.requests) == 4
    finally:
        await http.close()


async def test_profile_failure_after_exchange_is_unknown(harness):
    build, _, _ = harness
    transport = RecordingTransport([CHANNEL_RESPONSES["GITHUB"][0], httpx.ReadTimeout("timeout")])
    service = await build(transport=transport)
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    with pytest.raises(AuthException) as error:
        await service.complete(
            "app-a", "GITHUB", [("code", "code"), ("state", request.state)], binding=BINDING
        )
    assert error.value.outcome == "unknown" and not error.value.retryable
    assert len(transport.requests) == 2


def test_registry_rejects_synchronous_and_false_capabilities():
    class Sync(OAuthProvider):
        capabilities = (ProviderCapability("SYNC"),)

        def exchange(self, code, flow):
            raise AssertionError("不能执行同步网络实现")

    class FalseRevoke(OAuthProvider):
        capabilities = (ProviderCapability("FALSE_REVOKE", revoke=True),)

    with pytest.raises(AuthException):
        AuthProviderRegistry().register(Sync)
    with pytest.raises(AuthException):
        AuthProviderRegistry().register(FalseRevoke)


async def test_foreign_loop_close_does_not_damage_owner(harness):
    build, _, _ = harness
    service = await build()

    def foreign():
        with pytest.raises(AuthException):
            asyncio.run(service.close())

    await asyncio.to_thread(foreign)
    assert service.is_ready and service._close_task is None
    await service.close()


@pytest.mark.parametrize(
    "source, response",
    [
        ("GITHUB", {"access_token": ACCESS, "expires_in": 600}),
        ("FEISHU", {"code": 0, "access_token": ACCESS, "expires_in": 600}),
        ("QQ", "access_token=" + ACCESS + "&expires_in=600"),
    ],
)
async def test_rotating_refresh_requires_new_refresh_token(harness, source, response):
    build, _, _ = harness
    config = client_config(source)
    transport = RecordingTransport([response])
    service = await build(configs=(config,), transport=transport)
    from framework.starter_auth.model.auth_tokens import AuthTokens

    tokens = AuthTokens(
        application_id=config.application_id,
        source=source,
        client_id=config.client_id,
        refresh_token=REFRESH,
        subject="123",
    )
    with pytest.raises(AuthException) as failure:
        await service.refresh(tokens)
    assert failure.value.error_code == Codes.RESPONSE and failure.value.outcome == "unknown"
    assert len(transport.requests) == 1


async def test_nonrotating_refresh_omission_uses_rfc_semantics(harness):
    build, _, _ = harness
    config = client_config("HUAWEI")
    service = await build(
        configs=(config,),
        transport=RecordingTransport([{"access_token": ACCESS, "expires_in": 600}]),
    )
    from framework.starter_auth.model.auth_tokens import AuthTokens

    tokens = AuthTokens(
        application_id=config.application_id,
        source=config.source,
        client_id=config.client_id,
        refresh_token=REFRESH,
        subject="123",
    )
    refreshed = await service.refresh(tokens)
    assert refreshed.refresh_token == tokens.refresh_token and refreshed.subject == "123"


@pytest.mark.parametrize("subject", ["", "other-user"])
async def test_refresh_does_not_hide_invalid_subject(harness, subject):
    build, _, _ = harness
    config = client_config("JD")
    transport = RecordingTransport(
        [{"access_token": ACCESS, "expires_in": 600, "open_id": subject}]
    )
    service = await build(configs=(config,), transport=transport)
    from framework.starter_auth.model.auth_tokens import AuthTokens

    tokens = AuthTokens(
        application_id=config.application_id,
        source=config.source,
        client_id=config.client_id,
        refresh_token=REFRESH,
        subject="123",
    )
    with pytest.raises(AuthException) as failure:
        await service.refresh(tokens)
    assert failure.value.outcome == "unknown" and len(transport.requests) == 1
