import ast

import pytest
from pydantic import ValidationError

from fixtures.config_factory import ConfigFactory
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from framework.starter_websocket.core.websocket_runtime import WebSocketRuntime
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app
from starter_websocket.provider_source import SOURCE


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled": True},
        {"instance_lease_seconds": 1},
        {"authorization_concurrency": 1},
        {"handler_concurrency": 100},
        {"heartbeat_timeout_seconds": 1},
    ],
)
def test_invalid_runtime_configuration(changes):
    values = ConfigFactory.values()["config"]["models"]["websocket"]
    with pytest.raises(ValidationError):
        WebSocketSettings.model_validate({**values, **changes})


async def test_disabled_websocket_registers_no_endpoint(config_dir, monkeypatch):
    async def unexpected(*args):
        raise AssertionError("disabled websocket acquired resources")

    monkeypatch.setattr(WebSocketRuntime, "open", unexpected)
    app = create_app(base_dir=config_dir({"banner": {"enabled": False}}), environ={})
    async with app.router.lifespan_context(app):
        assert app.state.websocket is None
        assert not any(route.path == "/api/ws" for route in app.routes)


@pytest.mark.parametrize("scenario", ["missing_ticket", "duplicate", "multi_worker"])
async def test_invalid_assembly_fails_before_endpoint(scenario, config_dir, module_package):
    source = SOURCE
    if scenario == "missing_ticket":
        lines = source.splitlines()
        node = next(
            node
            for node in ast.parse(source).body
            if isinstance(node, ast.ClassDef) and node.name == "Tickets"
        )
        first = min(node.lineno, *(item.lineno for item in node.decorator_list))
        source = "\n".join(
            line for index, line in enumerate(lines, 1) if not first <= index <= node.end_lineno
        )
    elif scenario == "duplicate":
        source += '\n@socket_handler(HandlerDefinition(audience="test",type="echo",payload=Payload,policy=read))\nclass Duplicate(EchoHandler):\n    pass\n'
    module_package("bad_socket", scan_roots=(".",), files={"components.py": source})
    config = {
        "banner": {"enabled": False},
        "modules": {
            "packages": ["framework", "bad_socket"],
            "enabled": ["framework", "bad_socket"],
        },
        "config": {
            "models": {
                "security": {"enabled": True},
                "websocket": {"enabled": True, "allowed_origins": ["https://test.example"]},
            }
        },
    }
    if scenario == "multi_worker":
        config["uvicorn"] = {"workers": 2}
        config["server"] = {"reload": False, "engine": "uvicorn"}
    app = create_app(base_dir=config_dir(config), environ={})
    with pytest.raises(BootstrapError):
        async with app.router.lifespan_context(app):
            pytest.fail("invalid websocket started")
    assert app.state.websocket is None


async def test_resource_startup_failure_cleans_owned_lease(config_dir, module_package, monkeypatch):
    import os

    from redis.asyncio import Redis

    from framework.starter_websocket.core.redis_socket_transport import RedisSocketTransport

    if "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("真实 Redis 实例未配置")
    module_package("failed_socket", scan_roots=(".",), files={"components.py": SOURCE})
    captured = []
    initialize = WebSocketRuntime.__init__

    def capture(self, *args, **kwargs):
        initialize(self, *args, **kwargs)
        captured.append(self)

    async def fail(self):
        raise OSError("controlled startup failure")

    monkeypatch.setattr(WebSocketRuntime, "__init__", capture)
    monkeypatch.setattr(RedisSocketTransport, "open", fail)
    app = create_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {
                    "packages": ["framework", "failed_socket"],
                    "enabled": ["framework", "failed_socket"],
                },
                "config": {
                    "models": {
                        "security": {"enabled": True},
                        "cache": {"enabled": True, "port": int(os.environ["DUSHAN_DP_REDIS_PORT"])},
                        "websocket": {
                            "enabled": True,
                            "transport": "redis",
                            "namespace": "startup-failure",
                            "allowed_origins": ["https://test.example"],
                            "signing_secret": "test-only-startup-failure-signing-key",
                        },
                    }
                },
            }
        ),
        environ={},
    )
    with pytest.raises(BootstrapError) as failure:
        async with app.router.lifespan_context(app):
            pytest.fail("failed startup accepted")
    assert isinstance(failure.value.__cause__, OSError)
    assert captured[0].phase == "closed"
    client = Redis(host="127.0.0.1", port=int(os.environ["DUSHAN_DP_REDIS_PORT"]))
    try:
        assert (
            await client.exists(captured[0].online.instance_key, captured[0].online.connections_key)
            == 0
        )
    finally:
        await client.aclose()
