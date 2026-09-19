"""仅供独立进程验证，包含退出控制端点，不是产品路由。"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import Request
from granian.constants import Interfaces
from granian.server.embed import Server as GranianServer


async def run(engine, port, evidence):
    if "DUSHAN_SECURITY_WHEEL_ROOT" in os.environ:
        # 测试环境的 editable .pth 也会添加源码，安装验证必须排除该重复来源。
        source_backend = Path(__file__).resolve().parents[3] / "dushan-admin-backend"
        sys.path[:] = [entry for entry in sys.path if Path(entry).resolve() != source_backend]
    import framework.starter_security.core.security_service as security_module
    from fixtures.starter_steps import StarterSteps
    from framework.starter_security.integration.security_access import SecurityAccess
    from framework.starter_web.routing.route_policy import RoutePolicy
    from server.starter_server import create_app

    (evidence / "origin.json").write_text(
        json.dumps({"security": security_module.__file__}), encoding="utf-8"
    )
    app = create_app(
        steps=StarterSteps.without_tenant(), access_provider=SecurityAccess(), engine=engine
    )

    @app.get("/__security_test/protected")
    @RoutePolicy(("read",), roles=("reader",))
    async def protected():
        principal = app.state.security.context.require()
        return {"account": principal.account_id}

    @app.post("/__security_test/logout")
    @RoutePolicy()
    async def logout(request: Request):
        await app.state.security.logout(request.headers["authorization"].split(" ", 1)[1])
        return {"revoked": True}

    @app.get("/__security_test/stats")
    @RoutePolicy.public()
    async def stats():
        return {
            "pid": os.getpid(),
            "token_reads": app.state.security.tokens.reads,
            "permission_reads": app.state.security.permissions.reads,
        }

    if engine == "uvicorn":
        host = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                proxy_headers=False,
                access_log=False,
                lifespan="on",
            )
        )
    else:
        host = GranianServer(
            app, address="127.0.0.1", port=port, interface=Interfaces.ASGI, log_access=False
        )

    @app.post("/__security_test/stop")
    @RoutePolicy.public()
    async def stop():
        if engine == "uvicorn":
            host.should_exit = True
        else:
            host.signal_handler_interrupt()
        return {"stopping": True}

    await host.serve()
    (evidence / "closed.json").write_text(
        json.dumps(
            {
                "ready": app.state.bootstrap.ready,
                "security_released": app.state.security is None,
                "database_released": app.state.database is None,
                "di_released": app.state.application_context is None,
                "logging_closed": not app.state.bootstrap.logging_starter.initialized,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.engine, args.port, args.evidence))
