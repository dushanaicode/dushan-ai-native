import asyncio
import importlib
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import Depends, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.definitions.enums.container_state_enum import ContainerStateEnum
from server.bootstrap.bootstrapper import BootstrapError
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS, BootstrapStepSpec

pytestmark = pytest.mark.unit


def setup_app(module_package, config_dir, *, environ=None, steps=None):
    module_package(
        "context_feature",
        name="context_feature",
        files={
            "resource.py": (
                "from framework.starter_di.decorators.components import service\n"
                "@service\n"
                "class Resource:\n"
                "    def __init__(self):\n        self.resource_ready = False\n"
                "    async def pre_destroy(self):\n        self.resource_ready = False\n"
            )
        },
        scan_roots=(".",),
    )
    root = config_dir(
        {
            "modules": {
                "packages": ["framework", "context_feature"],
                "enabled": ["framework", "context_feature"],
            }
        }
    )
    resource_type = importlib.import_module("context_feature.resource").Resource
    return create_public_app(
        base_dir=root, environ={} if environ is None else environ, steps=steps
    ), resource_type


def test_http_and_websocket_parameter_injection_share_lookup(module_package, config_dir):
    app, resource_type = setup_app(module_package, config_dir)

    @app.get("/lookup")
    def lookup(resource=Depends(DiDependency(resource_type))):
        return {"same": resource is get_bean(resource_type)}

    @app.websocket("/socket")
    async def websocket(socket: WebSocket, resource=Depends(DiDependency(resource_type))):
        await socket.accept()
        await socket.send_json({"same": resource is get_bean(resource_type)})
        await socket.close()

    with TestClient(app) as client:
        assert client.get("/lookup").json() == {"same": True}
        with client.websocket_connect("/socket") as socket:
            assert socket.receive_json() == {"same": True}
        assert app.state.application_context.get_statistics()["executions"] == 0


def test_yaml_switches_control_real_lookup_and_automatic_binding(module_package, config_dir):
    app, resource_type = setup_app(
        module_package, config_dir, environ={"DI_LOOKUP_ENABLED": "false"}
    )

    @app.get("/injected")
    def injected(resource=Depends(DiDependency(resource_type))):
        return {"exists": resource is not None}

    @app.get("/lookup")
    def lookup():
        return get_bean(resource_type)

    with TestClient(app) as client:
        assert client.get("/injected").json() == {"exists": True}
        assert client.get("/lookup").json()["code"] == DiErrorCodes.LOOKUP_DISABLED.code

    manual, resource_type = setup_app(
        module_package, config_dir, environ={"DI_AUTOMATIC_CONTEXT_BINDING": "false"}
    )

    @manual.get("/missing")
    def missing():
        return get_bean(resource_type)

    @manual.get("/manual")
    def explicitly_bound():
        with manual.state.application_context.execution():
            return {"exists": get_bean(resource_type) is not None}

    with TestClient(manual) as client:
        assert client.get("/missing").json()["code"] == DiErrorCodes.CONTEXT_MISSING.code
        assert client.get("/manual").json() == {"exists": True}


async def test_stream_keeps_context_and_drain_waits_until_last_body(module_package, config_dir):
    app, resource_type = setup_app(module_package, config_dir, environ={"SERVER_ENGINE": "uvicorn"})
    entered, release = asyncio.Event(), asyncio.Event()

    @app.get("/stream")
    async def stream():
        async def chunks():
            initial = get_bean(resource_type)
            entered.set()
            yield b"first\n"
            await release.wait()
            assert get_bean(resource_type) is initial
            yield b"last\n"

        return StreamingResponse(chunks(), media_type="text/event-stream")

    async with app.router.lifespan_context(app):
        current = app.state.application_context
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            request = asyncio.create_task(client.get("/stream"))
            await asyncio.wait_for(entered.wait(), 5)
            draining = asyncio.create_task(current.drain())
            await asyncio.sleep(0.01)
            assert not draining.done() and current.get_statistics()["executions"] == 1
            rejected = await client.get("/health")
            assert rejected.status_code == 503
            rejected_normal = await client.get("/other")
            assert rejected_normal.status_code == 200
            assert rejected_normal.json()["code"] == DiErrorCodes.NOT_READY.code
            assert rejected_normal.headers["cache-control"] == "no-store"
            release.set()
            assert (await request).content == b"first\nlast\n"
            await draining


def test_resource_step_uses_context_before_ready_and_cleans_before_container(
    module_package, config_dir
):
    events = []

    @asynccontextmanager
    async def resource_step(ctx):
        current = ApplicationContext.current()
        assert current.state is ApplicationStateEnum.STARTING and not ctx.ready
        resource = get_bean(resource_type)
        resource.resource_ready = True
        events.append("resource started")
        try:
            yield
        finally:
            assert get_bean(resource_type) is resource
            assert not ctx.ready
            events.append("resource stopped")

    steps = (*APP_BOOTSTRAP_STEPS, BootstrapStepSpec("资源", resource_step, requires_di=True))
    app, resource_type = setup_app(module_package, config_dir, steps=steps)
    with TestClient(app) as client:
        current = app.state.application_context
        with current.execution():
            resource = get_bean(resource_type)
            assert resource.resource_ready
        assert client.get("/health").status_code == 200
    assert events == ["resource started", "resource stopped"] and not resource.resource_ready


def test_required_resource_step_rejects_disabled_di_before_running(module_package, config_dir):
    @asynccontextmanager
    async def resource_step(ctx):
        pytest.fail("DI 未启用不能初始化依赖它的资源")
        yield

    steps = (*APP_BOOTSTRAP_STEPS, BootstrapStepSpec("必需 DI", resource_step, requires_di=True))
    app, _ = setup_app(module_package, config_dir, environ={"DI_ENABLED": "false"}, steps=steps)
    with pytest.raises(BootstrapError), TestClient(app):
        pass
    assert not app.state.bootstrap.ready and app.state.application_context is None


async def test_host_cancellation_during_lifespan_exit_keeps_drain_resource_and_config_order(
    module_package, config_dir
):
    """宿主取消 lifespan 退出：先排空，再资源步骤、DI 销毁、配置关闭，最后传播取消。"""
    events = []
    started, stop = asyncio.Event(), asyncio.Event()

    @asynccontextmanager
    async def resource_step(ctx):
        events.append("resource started")
        try:
            yield
        finally:
            current = ctx.definitions.application_context
            assert current.state is ApplicationStateEnum.DRAINING
            assert current.get_statistics()["executions"] == 0
            events.append("resource stopped")

    steps = (*APP_BOOTSTRAP_STEPS, BootstrapStepSpec("资源", resource_step, requires_di=True))
    app, _ = setup_app(module_package, config_dir, steps=steps)

    async def host():
        async with app.router.lifespan_context(app):
            started.set()
            await stop.wait()

    hosting = asyncio.create_task(host())
    await started.wait()
    current = app.state.application_context
    configuration = app.state.bootstrap.definitions.configuration
    binding = current.reserve_execution()
    stop.set()
    for _ in range(200):
        if current.state is ApplicationStateEnum.DRAINING:
            break
        await asyncio.sleep(0.01)
    assert current.state is ApplicationStateEnum.DRAINING and events == ["resource started"]
    hosting.cancel("宿主要求退出")
    await asyncio.sleep(0.05)
    # 资源所有者受保护等待：取消不会提前释放资源步骤、容器或配置。
    assert not hosting.done() and events == ["resource started"]
    assert current.container.state is ContainerStateEnum.READY and configuration.revision >= 0
    current.release_execution(binding)
    with pytest.raises(asyncio.CancelledError):
        await hosting
    assert events == ["resource started", "resource stopped"]
    assert current.state is ApplicationStateEnum.CLOSED
    assert current.container.state is ContainerStateEnum.CLOSED
    with pytest.raises(BootstrapConfigError):
        _ = configuration.revision
