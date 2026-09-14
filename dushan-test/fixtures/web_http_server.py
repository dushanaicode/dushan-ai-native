import argparse
import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from granian.constants import Interfaces
from granian.server.embed import Server as GranianServer

from framework.common.security.request_identity import RequestIdentity
from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app


async def run(engine, port, evidence):
    bearer = HTTPBearer(auto_error=False)

    async def authorize(
        scopes: SecurityScopes, credentials: HTTPAuthorizationCredentials | None = Security(bearer)
    ):
        if credentials is None:
            return None
        if scopes.scopes != ["read"] or credentials.credentials != "fixture-token":
            raise HTTPException(403)
        return RequestIdentity(principal_id="fixture-user", tenant_id="fixture-tenant")

    app = create_app(access_provider=authorize, engine=engine)
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

    @app.post("/__stop")
    @RoutePolicy.public()
    async def stop():
        # 私有测试宿主控制现有引擎退出；不进入产品应用。
        if engine == "uvicorn":
            host.should_exit = True
        else:
            host.signal_handler_interrupt()
        return {"stopping": True}

    await host.serve()
    (evidence / "host-closed.json").write_text(
        json.dumps(
            {
                "ready": app.state.bootstrap.ready,
                "di_released": app.state.application_context is None,
                "definitions_released": app.state.bootstrap.definitions is None,
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
    arguments = parser.parse_args()
    asyncio.run(run(arguments.engine, arguments.port, arguments.evidence))
