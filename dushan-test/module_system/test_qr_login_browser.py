import asyncio
import json
import os
import socket
from pathlib import Path

import pytest
import uvicorn


@pytest.fixture(scope="module")
def qr_browser_ports():
    values = []
    for _ in range(2):
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            values.append(candidate.getsockname()[1])
    return values


@pytest.fixture(scope="module")
def system_allowed_origins(qr_browser_ports):
    return [f"http://localhost:{qr_browser_ports[1]}", f"http://127.0.0.1:{qr_browser_ports[1]}"]


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.skipif(os.environ.get("DUSHAN_QR_BROWSER") != "1", reason="按需启动扫码登录浏览器宿主")
async def test_qr_browser_host(system_app, qr_browser_ports):
    work = Path.cwd() / "Temp/qr-login-production/browser"
    work.mkdir(parents=True, exist_ok=True)
    api_port, web_port = qr_browser_ports
    server = uvicorn.Server(
        uvicorn.Config(
            system_app,
            host="127.0.0.1",
            port=api_port,
            lifespan="off",
            access_log=False,
            log_level="warning",
            log_config=None,
        )
    )
    task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(20):
            while not server.started:
                await asyncio.sleep(0.1)
        (work / "server.json").write_text(
            json.dumps({"apiPort": api_port, "webPort": web_port}), encoding="utf-8"
        )
        async with asyncio.timeout(1800):
            while not (work / "stop.request").exists():
                await asyncio.sleep(0.3)
    finally:
        server.should_exit = True
        await task
