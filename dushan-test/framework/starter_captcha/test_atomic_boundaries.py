import asyncio

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException


async def test_challenge_expiring_during_verification_cannot_mint_proof(
    captcha, stored_answer, monkeypatch
):
    challenge = await captcha.create("login")
    answer = await stored_answer(captcha, challenge)
    store = captcha.store
    client = store.cache.get_client(store.key)
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "challenge", challenge.token)
    )

    async def delayed(*args):
        await client.pexpire(key, 10)
        await asyncio.sleep(0.03)
        return True

    monkeypatch.setattr(captcha._provider, "verify", delayed)
    with pytest.raises(CaptchaException) as error:
        await captcha.check(challenge.token, "login", answer)
    assert error.value.error_code == Codes.EXPIRED
    assert not [item async for item in client.scan_iter(match="captcha:login:verification:*")]


async def test_provider_timeout_never_creates_verification(captcha, stored_answer, monkeypatch):
    challenge = await captcha.create("login")
    answer = await stored_answer(captcha, challenge)

    async def timeout(*args):
        raise CaptchaException(Codes.PROVIDER_TIMEOUT)

    monkeypatch.setattr(captcha._provider, "verify", timeout)
    with pytest.raises(CaptchaException) as error:
        await captcha.check(challenge.token, "login", answer)
    assert error.value.error_code == Codes.PROVIDER_TIMEOUT
    store = captcha.store
    client = store.cache.get_client(store.key)
    assert not [item async for item in client.scan_iter(match="captcha:login:verification:*")]


async def test_cache_client_failure_is_wrapped_by_real_cache_layer(captcha, monkeypatch):
    client = captcha.store.cache.get_client(captcha.store.key)

    async def fail(*args):
        raise RedisConnectionError("raw-sensitive-command")

    monkeypatch.setattr(client, "eval", fail)
    with pytest.raises(CaptchaException) as error:
        await captcha.consume("x" * 43, "login")
    assert error.value.error_code == Codes.CACHE_UNAVAILABLE
    assert isinstance(error.value.__cause__.__cause__, RedisConnectionError)


async def test_corrupt_verification_never_passes(captcha, stored_answer):
    challenge = await captcha.create("login")
    proof = await captcha.check(challenge.token, "login", await stored_answer(captcha, challenge))
    store = captcha.store
    client = store.cache.get_client(store.key)
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "verification", proof.verification)
    )
    await client.set(key, "wrong-provider", ex=30)
    with pytest.raises(CaptchaException) as error:
        await captcha.consume(proof.verification, "login")
    assert error.value.error_code == Codes.CORRUPT


async def test_wrong_purpose_does_not_burn_other_purpose_attempt(captcha, stored_answer):
    challenge = await captcha.create("login")
    answer = await stored_answer(captcha, challenge)
    with pytest.raises(CaptchaException):
        await captcha.check(challenge.token, "register", answer)
    with pytest.raises(CaptchaException) as error:
        await captcha.create("unconfigured")
    assert error.value.error_code == Codes.INVALID_INPUT
    store = captcha.store
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "challenge", challenge.token)
    )
    assert await store.cache.get_client(store.key).hget(key, "remaining") == "3"


async def test_optional_trace_receives_no_answers_or_tokens(
    captcha_app, stored_answer, monkeypatch
):
    from contextlib import contextmanager

    from opentelemetry import trace

    spans = []

    class TestTracer:
        @contextmanager
        def start_as_current_span(self, name, **kwargs):
            spans.append((name, kwargs))
            yield

    monkeypatch.setattr(trace, "get_tracer", lambda *args: TestTracer())
    app = await captcha_app(tracing_enabled=True)
    with app.state.application_context.execution():
        service = app.state.captcha
        challenge = await service.create("login")
        proof = await service.check(
            challenge.token, "login", await stored_answer(service, challenge)
        )
        await service.consume(proof.verification, "login")
        assert [name for name, _ in spans] == ["captcha.create", "captcha.check", "captcha.consume"]
        assert challenge.token not in repr(spans) and proof.verification not in repr(spans)
        assert all(
            not kw["record_exception"] and not kw["set_status_on_exception"] for _, kw in spans
        )
