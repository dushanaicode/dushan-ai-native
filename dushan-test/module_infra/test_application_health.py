import asyncio
import time
from contextvars import Context
from uuid import uuid4

import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient

from server.routing.application_health import ApplicationHealth
from server.starter_server import StarterServer

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(loop_scope="module")
async def health_app(infra_app, tmp_path_factory):
    values = yaml.safe_load(
        (infra_app.state.bootstrap.base_dir / "application.yaml").read_text(encoding="utf-8")
    )
    models = values["config"]["models"]
    values["banner"]["enabled"] = False
    namespace = "health-" + uuid4().hex
    for name in ("job", "mq", "websocket"):
        models[name]["namespace"] = namespace + "-" + name
    models["websocket"]["transport"] = "redis"
    folder = tmp_path_factory.mktemp("health-config")
    (folder / "application.yaml").write_text(
        yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
    )
    app = StarterServer.create_app(base_dir=folder, app_env="dev", environ={})
    async with app.router.lifespan_context(app):
        await wait_ready(app)
        yield app


async def health(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        return await client.get("/health")


async def wait_ready(app):
    async with asyncio.timeout(6):
        while True:
            response = await health(app)
            if response.status_code == 200:
                return
            await asyncio.sleep(0.03)


async def test_enabled_components_are_required_and_healthy(health_app):
    response = await health(health_app)
    assert response.status_code == 200
    assert response.json()["data"]["components"] == dict.fromkeys(
        ("bootstrap", "database", "cache", "job", "mq", "websocket"), "ready"
    )


@pytest.mark.parametrize("component", ["database", "cache", "job", "mq", "websocket"])
async def test_enabled_missing_runtime_is_unhealthy(health_app, monkeypatch, component):
    with monkeypatch.context() as patch:
        patch.setattr(health_app.state, component, None)
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"][component] == "not_ready"
    restored = await health(health_app)
    assert restored.status_code == 200, restored.text


@pytest.mark.parametrize("task_name", ["_loop_task", "_renew_task"])
async def test_job_background_task_exit_is_unhealthy(health_app, task_name):
    runtime = health_app.state.job
    task = getattr(runtime, task_name)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    try:
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["job"] == "not_ready"
    finally:
        callback = runtime._loop if task_name == "_loop_task" else runtime._renew
        setattr(runtime, task_name, asyncio.create_task(callback(), context=Context()))
    restored = await health(health_app)
    assert restored.status_code == 200, restored.text


async def test_paused_scheduler_is_unhealthy(health_app):
    runtime = health_app.state.job
    runtime.scheduler.pause()
    try:
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["job"] == "not_ready"
    finally:
        runtime.scheduler.resume()


async def test_job_standby_and_owner_are_both_healthy(health_app):
    """等待选主收敛，校验实际一主一备及 Redis 租约，不绑定固定进程归属。"""
    other = StarterServer.create_app(base_dir=health_app.state.bootstrap.base_dir, environ={})
    async with other.router.lifespan_context(other):
        for app in (health_app, other):
            await wait_ready(app)
            response = await health(app)
            assert response.status_code == 200, response.text
            assert response.json()["data"]["components"]["job"] == "ready"
        runtimes = (health_app.state.job, other.state.job)
        assert sum(runtime.owner for runtime in runtimes) == 1
        owner = next(runtime for runtime in runtimes if runtime.owner)
        standby = next(runtime for runtime in runtimes if not runtime.owner)
        assert owner.lease.is_valid and not standby.lease.is_valid
        assert owner.lease.key == standby.lease.key
        with owner.application.execution():
            client = owner.cache.get_client(owner.settings.owner_key())
        assert await client.get(owner.lease.key) == owner.lease.owner_token


async def test_mq_consumer_exit_and_hold_are_unhealthy(health_app):
    runtime = health_app.state.mq
    key, actor = next(iter(runtime.actors.items()))
    handler = next(item for item in runtime.registry.active() if item.__mq_consumer__.key == key)
    actor.cancel()
    await asyncio.gather(actor, return_exceptions=True)
    try:
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["mq"] == "not_ready"
    finally:
        runtime.actors[key] = asyncio.create_task(runtime._consume(handler), context=Context())
    runtime.paused.add(key)
    try:
        assert (await health(health_app)).json()["data"]["components"]["mq"] == "not_ready"
    finally:
        runtime.paused.remove(key)
        # HOLD 是永久停止语义，测试恢复时重新启动这个本轮接收循环。
        runtime.actors[key].cancel()
        await asyncio.gather(runtime.actors[key], return_exceptions=True)
        runtime.actors[key] = asyncio.create_task(runtime._consume(handler), context=Context())
    await wait_ready(health_app)


@pytest.mark.parametrize("task_name", ["_heartbeat", "_lease", "transport"])
async def test_websocket_background_exit_is_unhealthy(health_app, task_name):
    runtime = health_app.state.websocket
    owner = runtime.transport if task_name == "transport" else runtime
    attribute = "task" if task_name == "transport" else task_name
    task = getattr(owner, attribute)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    try:
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["websocket"] == "not_ready"
    finally:
        if task_name == "transport":
            await owner.open()
        else:
            callback = runtime._heartbeats if task_name == "_heartbeat" else runtime._renew
            setattr(owner, attribute, asyncio.create_task(callback(), context=Context()))
    restored = await health(health_app)
    assert restored.status_code == 200, restored.text


async def test_redis_timeout_is_bounded_and_recovers_without_messages(health_app, monkeypatch):
    with health_app.state.application_context.execution():
        client = health_app.state.cache.get_default_client()
    monkeypatch.setattr(ApplicationHealth, "PROBE_TIMEOUT_SECONDS", 0.15)
    await client.client_pause(800, "ALL")
    started = time.monotonic()
    response = await health(health_app)
    assert response.status_code == 503
    assert response.json()["data"]["components"]["cache"] == "not_ready"
    assert response.json()["data"]["components"]["mq"] == "not_ready"
    assert time.monotonic() - started < 0.7
    await client.ping()
    async with asyncio.timeout(5):
        while (await health(health_app)).status_code != 200:
            await asyncio.sleep(0.03)


async def test_websocket_lost_lease_is_unhealthy_even_with_live_broadcast(health_app):
    runtime = health_app.state.websocket
    await runtime.online.client.delete(runtime.online.instance_key)
    try:
        await asyncio.wait_for(asyncio.shield(runtime._lease), 6)
        assert runtime.transport.is_ready
        response = await health(health_app)
        assert response.status_code == 503
        assert response.json()["data"]["components"]["websocket"] == "not_ready"
    finally:
        await runtime.online.open()
        runtime._lease = asyncio.create_task(runtime._renew(), context=Context())
    await wait_ready(health_app)


async def test_shutdown_during_probe_cannot_report_ready(health_app, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    original = health_app.state.cache.check_health

    async def blocked():
        entered.set()
        await release.wait()
        return await original()

    with monkeypatch.context() as patch:
        patch.setattr(health_app.state.cache, "check_health", blocked)
        request = asyncio.create_task(health(health_app))
        await asyncio.wait_for(entered.wait(), 2)
        patch.setattr(health_app.state.bootstrap, "ready", False)
        release.set()
        response = await request
        assert response.status_code == 503
        assert response.json()["data"]["components"]["bootstrap"] == "not_ready"


async def test_probe_cancellation_is_not_swallowed(health_app, monkeypatch):
    entered = asyncio.Event()
    finished = asyncio.Event()

    async def blocked():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    monkeypatch.setattr(health_app.state.cache, "check_health", blocked)
    request = asyncio.create_task(health(health_app))
    await asyncio.wait_for(entered.wait(), 2)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    await asyncio.wait_for(finished.wait(), 2)
