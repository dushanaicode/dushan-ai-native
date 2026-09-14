import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from fixtures.config_factory import ConfigFactory
from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings
from server.launcher.granian_launcher import build_granian_cmd
from server.launcher.uvicorn_launcher import build_uvicorn_cmd

BACKEND_ROOT = Path(__file__).resolve().parents[3] / "dushan-admin-backend"

APPLICATION = """from fastapi import Depends, Request
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app

app = create_app(app_env="test")

@app.get("/client-ip")
@RoutePolicy.public()
async def client_ip(request: Request, settings=Depends(DiDependency(IpSettings))):
    peer = request.client.host
    return {
        "peer": peer,
        "scope_scheme": request.scope["scheme"],
        "ip": ClientIpResolver.resolve_client_ip(request.headers, peer, settings.trusted_proxy_cidrs),
        "scheme": ClientIpResolver.resolve_request_scheme(request.headers, peer, settings.trusted_proxy_cidrs, request.scope["scheme"]),
    }
"""


@pytest.mark.smoke
@pytest.mark.parametrize("engine", ["uvicorn", "granian"])
@pytest.mark.parametrize("trusted", [False, True])
def test_real_engine_preserves_peer_and_applies_proxy_policy(engine, trusted, config_dir, tmp_path):
    """复用真实启动参数和 Native DI，验证引擎没有在组件之前信任转发头。"""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    root = config_dir(
        {
            "server": {"port": port, "reload": False},
            "config": {
                "models": {"ip": {"trusted_proxy_cidrs": ["127.0.0.0/8"] if trusted else []}}
            },
        }
    )
    module = tmp_path / "client_ip_probe.py"
    module.write_text(APPLICATION, encoding="utf-8")
    server = ConfigFactory.build(ServerSettings, "server", port=port, reload=False)
    if engine == "uvicorn":
        command = build_uvicorn_cmd(
            server, ConfigFactory.build(UvicornSettings, "uvicorn", workers=1)
        )
    else:
        command = build_granian_cmd(
            server, ConfigFactory.build(GranianSettings, "granian", workers=1)
        )
    command[command.index("server.starter_server:app")] = "client_ip_probe:app"
    env = dict(
        os.environ,
        SERVER_ENV="test",
        SERVER_ENGINE=engine,
        DUSHAN_CONFIG_DIR=str(root),
        PYTHONPATH=os.pathsep.join((str(tmp_path), str(BACKEND_ROOT))),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
    )
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    log_path = tmp_path / f"{engine}-proxy.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=BACKEND_ROOT.parent,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            **options,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("代理验证服务提前退出：" + log_path.read_text(encoding="utf-8"))
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                        assert json.load(response)["data"]["status"] == "ready"
                        break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.1)
            else:
                pytest.fail("代理验证服务启动超时：" + log_path.read_text(encoding="utf-8"))
            scenarios = (
                (
                    {
                        "X-Forwarded-For": "203.0.113.9, 198.51.100.10, 127.0.0.3",
                        "X-Forwarded-Proto": "https",
                    },
                    "198.51.100.10",
                    "https",
                ),
                ({"Forwarded": 'for="[2001:4860:4860::8888]"'}, "2001:4860:4860::8888", "http"),
                ({"X-Forwarded-For": "invalid, 127.0.0.3"}, "127.0.0.1", "http"),
            )
            for headers, address, scheme in scenarios:
                request = Request(f"http://127.0.0.1:{port}/client-ip", headers=headers)
                with urlopen(request, timeout=3) as response:
                    result = json.load(response)
                assert result == {
                    "peer": "127.0.0.1",
                    "scope_scheme": scheme if trusted else "http",
                    "ip": address if trusted else "127.0.0.1",
                    "scheme": scheme if trusted else "http",
                }
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
