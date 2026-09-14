import asyncio

import httpx
import pytest
from fastapi import APIRouter, Request
from pydantic import ValidationError

from framework.starter_protection.exception.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.ratelimiter.rate_limit_rule import RateLimitRule
from framework.starter_protection.web.rate_limit import rate_limit


def make_rule(policy=None, *, capacity=10, algorithm="fixed"):
    return RateLimitRule(
        algorithm=algorithm, capacity=capacity, window_ms=3000, failure_policy=policy
    )


def assert_policy_result(result, expected):
    if expected == "allow":
        assert result.status == "degraded"
        assert result.reservation is None
    else:
        assert isinstance(result, ProtectionException)
        assert result.error_code == Codes.UNAVAILABLE


def test_missing_override_is_not_a_second_deployment_default(settings):
    rule = RateLimitRule(algorithm="fixed", capacity=10, window_ms=3000)
    assert rule.failure_policy is None
    assert "failure_policy" not in rule.model_fields_set
    assert settings().rate_failure_policy == "block"
    values = settings(rate_failure_policy="allow").model_dump()
    del values["rate_failure_policy"]
    with pytest.raises(ValidationError):
        type(settings()).model_validate(values)
    with pytest.raises(ValidationError):
        rule.failure_policy = "allow"


@pytest.mark.parametrize("invalid", ["PASS", "BLOCK", "pass", "", True, 1])
def test_override_rejects_unknown_policies(invalid):
    with pytest.raises(ValidationError):
        make_rule(invalid)


@pytest.mark.parametrize("method", ["acquire", "reserve"])
@pytest.mark.parametrize("default", ["block", "allow"])
@pytest.mark.parametrize("override", [None, "block", "allow"])
async def test_rule_override_and_yaml_default_apply_to_failure_and_open_circuit(
    services, subject, response_gate, method, default, override
):
    service = await services(
        cache_overrides={"port": response_gate.port},
        rate_failure_policy=default,
        circuit_failure_threshold=1,
    )
    rule = make_rule(override)
    action = getattr(service.rate_limiter, method)
    await response_gate.close()
    expected = default if override is None else override
    first = (await asyncio.gather(action("policy", subject, rule=rule), return_exceptions=True))[0]
    assert_policy_result(first, expected)
    if expected == "block":
        assert first.__cause__ is not None
    assert service.rate_limiter.circuit.open_until > 0
    again = (await asyncio.gather(action("policy", subject, rule=rule), return_exceptions=True))[0]
    assert_policy_result(again, expected)
    if expected == "block":
        assert again.context["reason"] == "circuit_open"
    assert service.settings.rate_failure_policy == default
    assert rule.failure_policy == override


async def test_concurrent_rule_overrides_do_not_mutate_application_policy(
    services, subject, response_gate
):
    service = await services(
        cache_overrides={"port": response_gate.port}, circuit_failure_threshold=1000
    )
    allow, block = make_rule("allow"), make_rule("block")
    await response_gate.close()
    results = await asyncio.gather(
        *(
            service.rate_limiter.acquire("mixed", subject, rule=allow if i % 2 == 0 else block)
            for i in range(40)
        ),
        return_exceptions=True,
    )
    for index, result in enumerate(results):
        assert_policy_result(result, "allow" if index % 2 == 0 else "block")
    assert service.settings.rate_failure_policy == "block"


@pytest.mark.parametrize(
    "method,algorithm", [("acquire", "fixed"), ("acquire", "sliding"), ("reserve", "fixed")]
)
async def test_allow_does_not_bypass_normal_quota_or_split_storage_keys(
    services, subject, method, algorithm
):
    service = await services()
    action = getattr(service.rate_limiter, method)
    block = make_rule("block", capacity=1, algorithm=algorithm)
    allow = make_rule("allow", capacity=1, algorithm=algorithm)
    acquired = await action("quota", subject, rule=block)
    assert acquired.status == "acquired"
    rejected = await action("quota", subject, rule=allow)
    assert rejected.status == "rejected" and rejected.retry_after_ms > 0
    client = service.runtime.cache.get_client(service.runtime.key)
    assert (
        len([key async for key in client.scan_iter(match=service.settings.key_prefix + ":rate:*")])
        == 1
    )
    if acquired.reservation is not None:
        assert await service.rate_limiter.release(acquired.reservation) == "released"


async def test_rule_policy_applies_to_timeout_without_replaying_writes(
    services, subject, response_gate
):
    direct = await services()
    service = await services(cache_overrides={"port": response_gate.port}, io_timeout_seconds=0.05)
    # 为两个并发命令先建好连接，故障门只拦截命令回包，不拦截新连接握手。
    pool = service.runtime.cache.get_client(service.runtime.key).connection_pool
    connections = [await pool.get_connection() for _ in range(2)]
    await asyncio.gather(*(pool.release(connection) for connection in connections))
    response_gate.pause()
    try:
        results = await asyncio.gather(
            service.rate_limiter.acquire("timeout", subject, rule=make_rule("allow")),
            service.rate_limiter.acquire("timeout", subject, rule=make_rule("block")),
            return_exceptions=True,
        )
        assert_policy_result(results[0], "allow")
        assert_policy_result(results[1], "block")
        assert results[1].context["reason"] == "timeout"
        assert response_gate.blocked.is_set()
    finally:
        response_gate.resume()
    client = direct.runtime.cache.get_client(direct.runtime.key)
    keys = [key async for key in client.scan_iter(match=direct.settings.key_prefix + ":rate:*")]
    assert len(keys) == 1 and await client.get(keys[0]) == "2"


async def test_allow_override_does_not_hide_redis_command_errors(services, subject):
    service = await services()
    rule = make_rule("allow")
    digest = service.runtime.identifier("corrupt", subject, ())
    identifier = f"rate:fixed:{rule.capacity}:{rule.window_ms}:{digest}"
    client = service.runtime.cache.get_client(service.runtime.key)
    await client.set(
        service.runtime.cache.build_full_key(service.runtime.key, identifier), "invalid"
    )
    with pytest.raises(ProtectionException) as caught:
        await service.rate_limiter.acquire("corrupt", subject, rule=rule)
    assert caught.value.context["reason"] == "command"
    assert service.rate_limiter.circuit.failures == 0


async def test_allow_override_does_not_hide_acl_errors(services, subject, namespace):
    admin = await services()
    client = admin.runtime.cache.get_client(admin.runtime.key)
    user = namespace + "_policy"
    try:
        await client.execute_command(
            "ACL", "SETUSER", user, "on", ">test-only-password", "~*", "+@all"
        )
        service = await services(
            cache_overrides={"username": user, "password": "test-only-password"}
        )
        await client.execute_command("ACL", "SETUSER", user, "-eval")
        with pytest.raises(ProtectionException) as caught:
            await service.rate_limiter.acquire("acl", subject, rule=make_rule("allow"))
        assert caught.value.error_code == Codes.UNAVAILABLE
        assert caught.value.context["reason"] in ("configuration", "command")
        assert service.rate_limiter.circuit.open_until == 0
    finally:
        await client.execute_command("ACL", "DELUSER", user)


async def test_allow_reservation_does_not_degrade_owner_cleanup(services, subject, response_gate):
    service = await services(
        cache_overrides={"port": response_gate.port}, rate_failure_policy="allow"
    )
    direct = await services()
    result = await service.rate_limiter.reserve("cleanup", subject, rule=make_rule("allow"))
    assert result.reservation is not None
    await response_gate.close()
    with pytest.raises(ProtectionException) as caught:
        await service.rate_limiter.release(result.reservation)
    assert caught.value.error_code == Codes.UNAVAILABLE
    assert await direct.rate_limiter.release(result.reservation) == "released"


@pytest.mark.parametrize("default", ["block", "allow"])
async def test_real_web_rules_each_resolve_policy_in_one_application(
    protection_app, response_gate, default
):
    router = APIRouter()
    calls = []

    async def endpoint(request: Request):
        calls.append(request.url.path)
        return {"executed": request.url.path}

    for path, rules in (
        ("/allow", (make_rule("allow"),)),
        ("/block", (make_rule("block"),)),
        ("/inherit", (make_rule(),)),
        ("/default", ()),
        ("/mixed", (make_rule("allow", capacity=2), make_rule("block", capacity=3))),
    ):
        router.add_api_route(path, rate_limit(path, rules=rules)(endpoint), methods=["GET"])
    app = await protection_app(
        routers=[router],
        overrides={
            "config": {
                "models": {
                    "cache": {"port": response_gate.port},
                    "protection": {"rate_failure_policy": default, "circuit_failure_threshold": 1},
                }
            }
        },
    )
    await response_gate.close()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.get("/allow")).json() == {"executed": "/allow"}
        for path in ("/block", "/mixed"):
            response = await client.get(path)
            assert response.status_code == 200 and response.json()["code"] == Codes.UNAVAILABLE.code
        for path in ("/inherit", "/default"):
            response = await client.get(path)
            assert response.status_code == 200
            if default == "allow":
                assert response.json() == {"executed": path}
            else:
                assert response.json()["code"] == Codes.UNAVAILABLE.code
    assert calls == (["/allow", "/inherit", "/default"] if default == "allow" else ["/allow"])


def test_conflicting_policies_do_not_allow_duplicate_quota_rules():
    with pytest.raises(ValueError):
        rate_limit("duplicate", rules=(make_rule("allow"), make_rule("block")))
