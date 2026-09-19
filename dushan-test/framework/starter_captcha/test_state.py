import asyncio
import json

import pytest

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_captcha.definitions.constants.captcha_error_codes import (
    CaptchaErrorCodes as Codes,
)
from framework.starter_captcha.exception.captcha_exception import CaptchaException


@pytest.mark.parametrize("provider", ["block_puzzle", "click_word"])
async def test_full_flow_and_one_time_business_credential(captcha_app, provider, stored_answer):
    app = await captcha_app(provider=provider)
    with app.state.application_context.execution():
        service = app.state.captcha
        challenge = await service.create("login")
        answer = await stored_answer(service, challenge)
        proof = await service.check(challenge.token, "login", answer)
        assert proof.expires_in == 60
        assert proof.verification not in repr(proof)
        with pytest.raises(CaptchaException) as error:
            await service.check(challenge.token, "login", answer)
        assert error.value.error_code == Codes.EXPIRED
        with pytest.raises(CaptchaException):
            await service.consume(challenge.token, "login")
        with pytest.raises(CaptchaException):
            await service.consume(proof.verification, "register")
        await service.consume(proof.verification, "login")
        with pytest.raises(CaptchaException) as error:
            await service.consume(proof.verification, "login")
        assert error.value.error_code == Codes.INVALID_VERIFICATION


async def test_wrong_answers_and_exhaustion(captcha):
    challenge = await captcha.create("login")
    for expected in [Codes.WRONG_ANSWER, Codes.WRONG_ANSWER, Codes.EXHAUSTED, Codes.EXHAUSTED]:
        with pytest.raises(CaptchaException) as error:
            await captcha.check(challenge.token, "login", {"points": [{"x": 0, "y": 0}]})
        assert error.value.error_code == expected


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {"points": []},
        {"points": [{"x": 2, "y": 0}] * 3},
        {"points": [{"x": 2, "y": 0}], "ticket": "x"},
        {"ticket": "x" * 4097},
        {"points": None},
        {"captcha_verify_param": "x" * 16385},
    ],
)
async def test_invalid_payload_uses_an_attempt(captcha, answer):
    challenge = await captcha.create("login")
    with pytest.raises(CaptchaException) as error:
        await captcha.check(challenge.token, "login", answer)
    assert error.value.error_code == Codes.INVALID_INPUT
    key = captcha.store.cache.build_full_key(
        captcha.store.key, captcha.store.identifier("login", "challenge", challenge.token)
    )
    assert await captcha.store.cache.get_client(captcha.store.key).hget(key, "remaining") == "2"


async def test_expiry_does_not_refresh_on_attempt(captcha, stored_answer):
    challenge = await captcha.create("login")
    answer = await stored_answer(captcha, challenge)
    store = captcha.store
    client = store.cache.get_client(store.key)
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "challenge", challenge.token)
    )
    await client.pexpire(key, 120)
    with pytest.raises(CaptchaException):
        await captcha.check(challenge.token, "login", {"points": [{"x": 0, "y": 0}]})
    assert 0 < await client.pttl(key) <= 120
    await asyncio.sleep(0.15)
    with pytest.raises(CaptchaException) as error:
        await captcha.check(challenge.token, "login", answer)
    assert error.value.error_code == Codes.EXPIRED
    challenge = await captcha.create("login")
    proof = await captcha.check(challenge.token, "login", await stored_answer(captcha, challenge))
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "verification", proof.verification)
    )
    await client.pexpire(key, 40)
    await asyncio.sleep(0.07)
    with pytest.raises(CaptchaException) as error:
        await captcha.consume(proof.verification, "login")
    assert error.value.error_code == Codes.INVALID_VERIFICATION


async def test_concurrent_challenge_and_verification_only_one_winner(captcha, stored_answer):
    challenge = await captcha.create("login")
    answer = await stored_answer(captcha, challenge)
    results = await asyncio.gather(
        *(captcha.check(challenge.token, "login", answer) for _ in range(30)),
        return_exceptions=True,
    )
    winners = [result for result in results if not isinstance(result, BaseException)]
    assert len(winners) == 1
    consumed = await asyncio.gather(
        *(captcha.consume(winners[0].verification, "login") for _ in range(40)),
        return_exceptions=True,
    )
    assert consumed.count(None) == 1
    assert all(isinstance(result, CaptchaException) for result in consumed if result is not None)


async def test_concurrent_incorrect_attempts_are_bounded(captcha):
    challenge = await captcha.create("login")
    outcomes = await asyncio.gather(
        *(
            captcha.check(challenge.token, "login", {"points": [{"x": 0, "y": 0}]})
            for _ in range(30)
        ),
        return_exceptions=True,
    )
    assert sum(error.error_code == Codes.WRONG_ANSWER for error in outcomes) == 2
    assert sum(error.error_code == Codes.EXHAUSTED for error in outcomes) == 28


@pytest.mark.parametrize("value", ["", "short", "x" * 44, "\n" + "x" * 42, 1, None])
async def test_illegal_tokens(captcha, value):
    with pytest.raises(CaptchaException) as error:
        await captcha.consume(value, "login")
    assert error.value.error_code == Codes.INVALID_VERIFICATION


@pytest.mark.parametrize("corruption", ["payload", "counter", "type", "ttl", "valid_wrong_shape"])
async def test_cache_corruption_distinguished(captcha, corruption):
    challenge = await captcha.create("login")
    store = captcha.store
    client = store.cache.get_client(store.key)
    key = store.cache.build_full_key(
        store.key, store.identifier("login", "challenge", challenge.token)
    )
    if corruption == "payload":
        await client.hset(key, "payload", "{broken")
    elif corruption == "counter":
        await client.hset(key, "remaining", "-1")
    elif corruption == "type":
        await client.set(key, "oops", ex=30)
    elif corruption == "ttl":
        await client.persist(key)
    else:
        await client.hset(
            key,
            "payload",
            json.dumps({"provider": "block_puzzle", "purpose": "login", "points": []}),
        )
    with pytest.raises(CaptchaException) as error:
        await captcha.check(challenge.token, "login", {"points": [{"x": 1, "y": 0}]})
    assert error.value.error_code == Codes.CORRUPT
    await client.delete(key)


async def test_cache_failure_propagates_without_success(captcha, monkeypatch):
    async def broken(*args, **kwargs):
        raise CacheException(CacheErrorCodes.OPERATION_FAILED, msg="private-answer-and-verification")

    monkeypatch.setattr(CacheHandler, "eval_atomic", broken)
    with pytest.raises(CaptchaException) as error:
        await captcha.create("login")
    assert error.value.error_code == Codes.CACHE_UNAVAILABLE
    assert error.value.__cause__ is not None


async def test_global_generation_counter_atomic(captcha_app):
    app = await captcha_app(generation_limit=3, generation_window_seconds=1)
    with app.state.application_context.execution():
        store = app.state.captcha.store
        results = await asyncio.gather(
            *(store.reserve_generation() for _ in range(50)), return_exceptions=True
        )
        assert results.count(None) == 3
        key = store.cache.build_full_key(store.key, "generation")
        client = store.cache.get_client(store.key)
        assert await client.get(key) == "3"
        assert 0 < await client.pttl(key) <= 1000
        await client.pexpire(key, 20)
        await asyncio.sleep(0.05)
        await store.reserve_generation()
        assert await client.get(key) == "1"
