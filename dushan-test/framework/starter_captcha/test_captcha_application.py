import asyncio
import threading

import httpx
import pytest
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.starter_captcha.core.captcha_service import CaptchaService
from framework.starter_captcha.definitions.constants.captcha_error_codes import (
    CaptchaErrorCodes as Codes,
)
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.exception.di_exception import DiException
from framework.starter_web.exception.response_builder import ExceptionResponseBuilder
from server.starter_server import create_app


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_attempts": 0},
        {"challenge_ttl_seconds": True},
        {"provider": "unknown"},
        {"purposes": []},
        {"purposes": ["login", "login"]},
        {"slider_tolerance": float("nan")},
        {"provider": "aliyun"},
        {"provider": "tencent"},
        {"generation_concurrency": 0},
        {"aliyun": {"region": "sgp"}},
    ],
)
def test_config_validation(settings, overrides):
    with pytest.raises(ValidationError):
        settings(**overrides)


async def test_disabled_app_starts_without_resources(config_dir):
    app = create_app(base_dir=config_dir({"banner": {"enabled": False}}), environ={})
    async with app.router.lifespan_context(app):
        with app.state.application_context.execution():
            service = get_bean(CaptchaService)
            assert service.configuration()["enabled"] is False
            assert service._pool is None and service._http is None
            with pytest.raises(CaptchaException) as error:
                await service.create("login")
            assert error.value.error_code == Codes.DISABLED


async def test_enabled_without_cache_fails_startup(config_dir):
    app = create_app(
        base_dir=config_dir(
            {"banner": {"enabled": False}, "config": {"models": {"captcha": {"enabled": True}}}}
        ),
        environ={},
    )
    with pytest.raises(Exception):
        async with app.router.lifespan_context(app):
            pytest.fail("启用验证码且没有可用缓存时不得启动成功")


async def test_multiple_workers_share_one_challenge_without_routing_affinity(
    captcha_app, stored_answer
):
    """两个应用实例代表同一服务的两个 worker：挑战必须能跨实例接续。

    实例是各自独立的对象，状态只在 Cache 里；负载均衡把 create 和 check 分到
    不同进程时，用户不能因此看到"验证码已过期"。
    """
    a, b = await captcha_app(), await captcha_app()
    with a.state.application_context.execution():
        first = get_bean(CaptchaService)
        challenge = await first.create("login")
        answer = await stored_answer(first, challenge)
    with b.state.application_context.execution():
        second = get_bean(CaptchaService)
        assert first is not second
        assert first.store.key.key == second.store.key.key
        # 在另一个实例上校验通过，并由它签发凭证。
        proof = await second.check(challenge.token, "login", answer)
    with a.state.application_context.execution():
        # 凭证再回到第一个实例消费，同样成立；消费后任何实例都不能重复消费。
        await first.consume(proof.verification, "login")
    with b.state.application_context.execution():
        with pytest.raises(CaptchaException):
            await second.consume(proof.verification, "login")


async def test_challenge_state_survives_service_restart(captcha_app, stored_answer):
    """实例重启不应作废仍在 TTL 内的挑战：状态属于 Cache，不属于进程。"""
    app = await captcha_app()
    with app.state.application_context.execution():
        service = get_bean(CaptchaService)
        challenge = await service.create("login")
        answer = await stored_answer(service, challenge)
    restarted = await captcha_app()
    with restarted.state.application_context.execution():
        fresh = get_bean(CaptchaService)
        proof = await fresh.check(challenge.token, "login", answer)
        await fresh.consume(proof.verification, "login")


async def test_http_di_lookup_and_shutdown(captcha_app, stored_answer):
    router = APIRouter()

    @router.get("/captcha-test")
    async def endpoint(service=Depends(DiDependency(CaptchaService))):
        assert service is get_bean(CaptchaService)
        return (await service.create("login")).model_dump()

    app = await captcha_app(routers=[router])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/captcha-test")
        assert response.status_code == 200
        assert set(response.json()) == {"token", "provider", "purpose", "expires_in", "data"}
    context = app.state.application_context

    async def resolve():
        return get_bean(CaptchaService)

    assert await context.tasks.run(resolve) is app.state.captcha


async def test_managed_inject_and_context_lookup_share_application(captcha_app, module_package):
    import importlib

    module_package(
        "captcha_consumer",
        files={
            "consumer.py": """
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_captcha.core.captcha_service import CaptchaService

@service
class Consumer:
    captcha: CaptchaService = Inject()
"""
        },
    )
    consumer_type = importlib.import_module("captcha_consumer.consumer").Consumer
    app = await captcha_app(
        app_overrides={
            "modules": {
                "packages": ["framework", "captcha_consumer"],
                "enabled": ["framework", "captcha_consumer"],
            }
        }
    )
    with app.state.application_context.execution():
        consumer = get_bean(consumer_type)
        assert consumer.captcha is get_bean(CaptchaService)
    with pytest.raises(DiException):
        get_bean(CaptchaService)


async def test_closing_one_application_leaves_other_usable(captcha_app):
    a, b = await captcha_app(), await captcha_app()
    context = a.state.application_context
    await a.state.captcha.close()
    with b.state.application_context.execution():
        assert (await get_bean(CaptchaService).create("login")).provider == "block_puzzle"
    with context.execution():
        with pytest.raises(CaptchaException):
            await get_bean(CaptchaService).create("login")


def test_sensitive_exception_projection_and_debug():
    secret = "opaqueCredentialAndAnswerSensitive"
    cause = ValueError(secret)
    error = CaptchaException(Codes.PROVIDER_RESPONSE, cause=cause)
    wrapped = RuntimeError(secret)
    wrapped.__cause__ = error
    for item in [error, wrapped, ExceptionGroup(secret, [wrapped])]:
        response = ExceptionResponseBuilder.build(
            Codes.PROVIDER_RESPONSE, Codes.PROVIDER_RESPONSE.description, exc=item, debug=True
        )
        assert secret not in str(response)
        projected = SafeExceptionDiagnostics.snapshot(item)
        assert secret not in str(projected)
    assert error.__cause__ is cause


@pytest.mark.parametrize("grouped", [False, True])
def test_native_loguru_pipeline_redacts_sensitive_causes(grouped):
    from io import StringIO

    from loguru import logger

    from framework.starter_logging.core.logger_configurator import LoggerConfigurator

    secret = "opaque-private-captcha-credential-answer"
    error = CaptchaException(Codes.CACHE_UNAVAILABLE, cause=ValueError(secret))
    if grouped:
        wrapper = RuntimeError(secret)
        wrapper.__cause__ = error
        error = ExceptionGroup(secret, [wrapper])
    output = StringIO()
    sink = logger.add(
        output, format="{message}{extra[exception_trace]}", backtrace=True, diagnose=True
    )
    try:
        logger.patch(LoggerConfigurator._patch_record).opt(exception=error).error("验证码依赖失败")
    finally:
        logger.remove(sink)
    assert "CaptchaException" in output.getvalue()
    assert secret not in output.getvalue()


async def test_generation_resource_bound_and_close(captcha, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = captcha._provider.create

    def slow(purpose):
        entered.set()
        release.wait(3)
        return original(purpose)

    monkeypatch.setattr(captcha._provider, "create", slow)
    tasks = [asyncio.create_task(captcha.create("login")) for _ in range(4)]
    while not entered.is_set():
        await asyncio.sleep(0.005)
    with pytest.raises(CaptchaException) as error:
        await captcha.create("login")
    assert error.value.error_code == Codes.CAPACITY
    tasks[0].cancel()
    await asyncio.gather(tasks[0], return_exceptions=True)
    assert captcha._generating == 4
    release.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    await captcha.close()
    assert captcha._pool is None and captcha._jobs == set()
    with pytest.raises(CaptchaException) as error:
        await captcha.create("login")
    assert error.value.error_code == Codes.UNAVAILABLE


async def test_cache_prefix_participates_in_cache_startup_validation(captcha_app):
    """按配置解析后的验证码键必须在连接创建前进入 Cache 的统一校验。"""
    from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
    from framework.starter_captcha.definitions.captcha_cache_keys import CaptchaCacheKeys

    app = await captcha_app()
    with app.state.application_context.execution():
        registry = get_bean(CacheKeyRegistry)
        service = get_bean(CaptchaService)
        declared = CaptchaCacheKeys.state(service.settings.client_name)
        assert registry.find(declared.key) == service.store.key == declared


async def test_store_keys_do_not_depend_on_the_application_instance(captcha_app):
    """同一挑战在任意实例上算出的缓存键必须一致，否则多 worker 无法接续。"""
    a, b = await captcha_app(), await captcha_app()
    with a.state.application_context.execution():
        first = get_bean(CaptchaService)
    with b.state.application_context.execution():
        second = get_bean(CaptchaService)
    token = "t" * 43
    for kind in ("challenge", "verification"):
        assert first.store.identifier("login", kind, token) == second.store.identifier(
            "login", kind, token
        )


@pytest.mark.parametrize("enabled", [False, True])
async def test_named_cache_client_without_default_starts(captcha_app, stored_answer, enabled):
    from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry

    app = await captcha_app(
        enabled=enabled,
        client_name="isolated",
        app_overrides={
            "config": {
                "models": {
                    "cache": {
                        "clients": [{"name": "isolated", "db": 0}],
                        "default_client": "isolated",
                    }
                }
            }
        },
    )
    with app.state.application_context.execution():
        assert await app.state.cache.get_default_client().ping()
        registry = get_bean(CacheKeyRegistry)
        if not enabled:
            assert registry.find("captcha") is None
            return
        service = get_bean(CaptchaService)
        assert registry.find("captcha") == service.store.key
        assert service.store.key.client_name == "isolated"
        challenge = await service.create("login")
        proof = await service.check(
            challenge.token, "login", await stored_answer(service, challenge)
        )
        await service.consume(proof.verification, "login")


async def test_cache_key_clients_are_resolved_per_application(captcha_app, stored_answer):
    from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry

    a = await captcha_app()
    b = await captcha_app(client_name="second")
    with a.state.application_context.execution():
        first = get_bean(CaptchaService)
        first_key = get_bean(CacheKeyRegistry).find("captcha")
        challenge = await first.create("login")
        answer = await stored_answer(first, challenge)
    with b.state.application_context.execution():
        second = get_bean(CaptchaService)
        assert get_bean(CacheKeyRegistry).find("captcha").client_name == "second"
        with pytest.raises(CaptchaException) as error:
            await second.check(challenge.token, "login", answer)
        assert error.value.error_code == Codes.EXPIRED
    with a.state.application_context.execution():
        assert get_bean(CacheKeyRegistry).find("captcha") is first_key
        assert first_key.client_name == "default"
        proof = await first.check(challenge.token, "login", answer)
        await first.consume(proof.verification, "login")


@pytest.mark.parametrize("phase", ["quota", "store", "verify", "complete", "consume"])
async def test_close_drains_the_entire_operation(captcha, stored_answer, monkeypatch, phase):
    """关闭必须等待线程提交前、Provider 校验及最后一次 Redis 操作。"""
    entered, release = asyncio.Event(), asyncio.Event()
    worker_threads = []
    provider_create = captcha._provider.create

    def record_worker(purpose):
        worker_threads.append(threading.current_thread().name)
        return provider_create(purpose)

    monkeypatch.setattr(captcha._provider, "create", record_worker)
    if phase in ("quota", "store"):
        owner = captcha.store
        method = "reserve_generation" if phase == "quota" else "create"
        operation = captcha.create("login")
    else:
        challenge = await captcha.create("login")
        answer = await stored_answer(captcha, challenge)
        if phase == "consume":
            proof = await captcha.check(challenge.token, "login", answer)
            owner, method = captcha.store, "consume"
            operation = captcha.consume(proof.verification, "login")
        else:
            owner = captcha._provider if phase == "verify" else captcha.store
            method = "verify" if phase == "verify" else "complete"
            operation = captcha.check(challenge.token, "login", answer)
    original = getattr(owner, method)

    async def paused(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(owner, method, paused)
    task = asyncio.create_task(operation)
    await asyncio.wait_for(entered.wait(), 3)
    pool = captcha._pool
    closing = asyncio.create_task(captcha.close())
    try:
        await asyncio.sleep(0)
        assert not closing.done() and captcha._pool is pool
        with pytest.raises(CaptchaException) as error:
            await captcha.create("login")
        assert error.value.error_code == Codes.UNAVAILABLE
    finally:
        release.set()
        await asyncio.wait_for(asyncio.gather(task, closing), 3)
    assert worker_threads and all(name.startswith("captcha") for name in worker_threads)
    assert captcha._pool is None and not captcha._jobs
    assert captcha._operations == captcha._generating == 0


async def test_cancelled_close_waiter_keeps_draining_operations(captcha, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    original = captcha.store.reserve_generation

    async def paused():
        entered.set()
        await release.wait()
        await original()

    monkeypatch.setattr(captcha.store, "reserve_generation", paused)
    task = asyncio.create_task(captcha.create("login"))
    await asyncio.wait_for(entered.wait(), 3)
    waiter = asyncio.create_task(captcha.close())
    try:
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert not captcha._close_task.done() and captcha._pool is not None
    finally:
        release.set()
        await asyncio.wait_for(asyncio.gather(task, captcha.close()), 3)
    assert captcha._pool is None and captcha._operations == 0
