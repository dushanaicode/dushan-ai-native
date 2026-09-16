import argparse
import asyncio
import json
from pathlib import Path

import uvicorn
from granian.constants import Interfaces
from granian.server.embed import Server as GranianServer

import framework
from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app


class NetworkGate:
    """真实 ASGI 链上的可控慢发送探针，只在测试请求显式启用。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        stalled = scope["type"] == "websocket" and (b"x-ws-test-stall", b"yes") in scope["headers"]

        async def controlled(message):
            if (
                stalled
                and message["type"] == "websocket.send"
                and json.loads(message["text"])["type"] == "echo"
            ):
                await asyncio.Event().wait()
            await send(message)

        await self.app(scope, receive, controlled)


async def run(arguments):
    app = create_app(base_dir=arguments.config, engine=arguments.engine)
    transport = NetworkGate(app)
    if arguments.engine == "uvicorn":
        host = uvicorn.Server(
            uvicorn.Config(
                transport,
                host="127.0.0.1",
                port=arguments.port,
                access_log=False,
                proxy_headers=False,
                lifespan="on",
                log_level="debug",
            )
        )
    else:
        host = GranianServer(
            transport,
            address="127.0.0.1",
            port=arguments.port,
            interface=Interfaces.ASGI,
            log_access=False,
        )
    runtime = None
    stop_errors = []

    @app.post("/__ws_stop")
    @RoutePolicy.public()
    async def stop():
        nonlocal runtime
        runtime = app.state.websocket
        if runtime is not None:
            try:
                await runtime.quiesce()
            except Exception as error:
                stop_errors.append(type(error).__name__)
        if arguments.engine == "uvicorn":
            host.should_exit = True
        else:
            host.stop()
        return {"stopping": True}

    await host.serve()
    (arguments.evidence / "closed.json").write_text(
        json.dumps(
            {
                "di_released": app.state.application_context is None,
                "ready": app.state.bootstrap.ready,
                "websocket": None if runtime is None else runtime.resources(),
                "stop_errors": stop_errors,
                "framework_root": str(Path(framework.__file__).resolve().parent),
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
