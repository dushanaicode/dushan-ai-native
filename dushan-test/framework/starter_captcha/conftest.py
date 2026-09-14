import json
from contextlib import AsyncExitStack

import pytest

from fixtures.cache_fixtures import REDIS_TARGET, redis_values
from fixtures.config_factory import ConfigFactory
from fixtures.public_web_app import create_public_app
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.core.captcha_service import CaptchaService
from framework.starter_web.routing.router_registration import RouterRegistration


@pytest.fixture
def settings():
    def build(**overrides):
        values = ConfigFactory.values()["config"]["models"]["captcha"]
        values.update(enabled=True)
        ConfigFactory.merge(values, overrides)
        return CaptchaSettings.model_validate(values)

    return build


@pytest.fixture
async def captcha_app(config_dir):
    if REDIS_TARGET is None:
        pytest.skip("需要 DUSHAN_CACHE_TEST_REDIS 指向真实 Redis")
    async with AsyncExitStack() as stack:

        async def build(*, app_overrides=None, routers=(), **overrides):
            values = {
                "banner": {"enabled": False},
                "config": {
                    "models": {"cache": redis_values(), "captcha": {"enabled": True, **overrides}}
                },
            }
            ConfigFactory.merge(values, app_overrides or {})
            app = create_public_app(
                base_dir=config_dir(values),
                environ={},
                routers=[RouterRegistration(router) for router in routers],
            )
            await stack.enter_async_context(app.router.lifespan_context(app))
            return app

        yield build


@pytest.fixture
def stored_answer():
    async def read(service, challenge):
        store = service.store
        key = store.cache.build_full_key(
            store.key, store.identifier(challenge.purpose, "challenge", challenge.token)
        )
        raw = await store.cache.get_client(store.key).hget(key, "payload")
        return {"points": json.loads(raw)["points"]}

    return read


@pytest.fixture
async def captcha(captcha_app):
    app = await captcha_app()
    with app.state.application_context.execution():
        yield app.state.application_context.get_bean(CaptchaService)


@pytest.fixture(autouse=True)
async def isolate_captcha_state():
    """用例之间清掉 captcha 前缀。

    挑战状态改为按前缀共享（多 worker 必须能互相接续）之后，生成配额等计数器
    不再随实例隔离，用例必须自己清场，否则前一条用例的计数会算到后一条头上。
    """
    yield
    if REDIS_TARGET is None:
        return
    from redis.asyncio import Redis

    for client_settings in REDIS_TARGET["clients"]:
        client = Redis(
            host=REDIS_TARGET["host"],
            port=REDIS_TARGET["port"],
            username=REDIS_TARGET.get("username"),
            password=REDIS_TARGET.get("password"),
            db=client_settings["db"],
            decode_responses=True,
        )
        try:
            keys = [key async for key in client.scan_iter(match="captcha:*", count=500)]
            if keys:
                await client.delete(*keys)
        finally:
            await client.aclose()
