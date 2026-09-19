import asyncio
import socket

import pytest
from httpx import AsyncClient
from uvicorn import Config, Server

from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes


@pytest.mark.parametrize("tenant_case", [{"enabled": True}, {"enabled": False}], indirect=True)
async def test_real_http_identity_target_headers_and_mode_routes(tenant_case):
    case = tenant_case
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    sock.setblocking(False)
    port = sock.getsockname()[1]
    server = Server(
        Config(
            case.app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            ws="none",
            log_config=None,
            access_log=False,
        )
    )
    serving = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                await asyncio.sleep(0.01)
        token, _ = case.issue()
        async with AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            response = await client.get(
                "/api/tenant-records", headers={"Authorization": "Bearer " + token}
            )
            assert response.json() == [1, 2]
            response = await client.get(
                "/api/tenant-records?target=2", headers={"Authorization": "Bearer " + token}
            )
            assert response.json()["code"] == TenantErrorCodes.DENIED.code
            response = await client.get(
                "/api/tenant-records",
                headers={"Authorization": "Bearer " + token, "tenant-id": "2"},
            )
            assert (
                response.json()["code"] == 403
            )  # 租户请求头由 TenantSelectorMiddleware 拒绝，属全局 403 协议守卫
            response = await client.get("/api/tenant-mode")
            if case.tenant.settings.enabled:
                assert response.json() == {"enabled": True}
            else:
                assert response.json()["code"] == 404
            assert (
                any(route.path == "/api/tenant-mode" for route in case.app.routes)
                is case.tenant.settings.enabled
            )
    finally:
        server.should_exit = True
        await serving
        sock.close()
