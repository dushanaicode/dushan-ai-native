import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]


def read_completed_stream(client, url, headers):
    """测试消费者按显式协议验证完成标记；正常 EOF 本身不代表业务成功。"""
    response = client.get(url, headers=headers)
    if not response.content.endswith(b"done\n"):
        raise ValueError("流缺少协议完成标记")
    return response


@pytest.mark.smoke
@pytest.mark.parametrize("engine", ["uvicorn", "granian"])
def test_real_web_protocols_disconnect_and_graceful_shutdown(engine, config_dir, tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    evidence = tmp_path / engine
    evidence.mkdir()
    (evidence / "data.bin").write_bytes(b"abcdef")
    root = config_dir(
        {
            "server": {"port": port, "reload": False, "engine": engine},
            "web": {
                "max_body_bytes": 4096,
                "max_multipart_bytes": 2_000_000,
                "cors_origins": ["https://ui.example"],
            },
            "modules": {
                "packages": ["framework", "fixtures.web_http_feature"],
                "enabled": ["framework", "web_http_feature"],
            },
            "config": {"models": {"ip": {"trusted_proxy_cidrs": ["127.0.0.1/32"]}}},
        }
    )
    env = dict(
        os.environ,
        DUSHAN_CONFIG_DIR=str(root),
        DUSHAN_WEB_EVIDENCE=str(evidence),
        SERVER_ENV="test",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
    )
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "dushan-admin-backend"), str(ROOT / "dushan-test")]
    )
    for key in ("TEMP", "TMP", "TMPDIR"):
        env[key] = str(evidence)
    log_path = evidence / "server.log"
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    successful = False
    with log_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-m",
                "fixtures.web_http_server",
                "--engine",
                engine,
                "--port",
                str(port),
                "--evidence",
                str(evidence),
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            **options,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False
            ) as client:
                deadline = time.monotonic() + 20
                while True:
                    assert process.poll() is None, log_path.read_text(encoding="utf-8")
                    try:
                        if client.get("/health").json()["data"]["status"] == "ready":
                            break
                    except (httpx.NetworkError, httpx.TimeoutException):
                        pass
                    assert time.monotonic() < deadline, log_path.read_text(encoding="utf-8")
                    time.sleep(0.05)
                info = client.get(
                    "/__web_test/info", headers={"X-Forwarded-For": "203.0.113.7"}
                ).json()
                assert info["data"]["ip"] == "203.0.113.7"
                assert info["data"]["engine"] == engine
                assert client.get("/__web_test/protected").json()["code"] == 401
                assert (
                    client.get(
                        "/__web_test/protected", headers={"Authorization": "Bearer fixture-token"}
                    ).json()["tenant_id"]
                    == "fixture-tenant"
                )
                response = client.get("/__web_test/file", headers={"Range": "bytes=2-4"})
                assert response.status_code == 206 and response.content == b"cde"
                assert response.headers["content-range"] == "bytes 2-4/6"
                for excel in (False, True):
                    known = client.get(
                        "/__web_test/known",
                        params={"excel": excel},
                        headers={"Accept-Encoding": "gzip"},
                    )
                    assert known.content == b"known-length" * 20_000
                    if engine == "granian":
                        assert known.headers["content-length"] == "240000"
                        assert "content-encoding" not in known.headers
                sse_response = client.get("/__web_test/events")
                assert "event: item" in sse_response.text and "event: done" in sse_response.text
                assert "content-encoding" not in sse_response.headers
                assert client.head("/__web_test/head").content == b""
                assert client.post("/__web_test/echo", content=iter([b"ab", b"cd"])).json() == {
                    "bytes": 4
                }
                assert (
                    client.post(
                        "/__web_test/echo", content=iter([b"a" * 3000, b"b" * 3000])
                    ).json()["code"]
                    == 413
                )
                upload = client.post(
                    "/__web_test/upload", files={"file": ("file.bin", b"x" * 1_100_000)}
                )
                assert upload.json() == {"bytes": 1_100_000, "rolled": True}
                assert (
                    client.options(
                        "/__web_test/info",
                        headers={
                            "Origin": "https://ui.example",
                            "Access-Control-Request-Method": "GET",
                        },
                    ).headers["access-control-allow-origin"]
                    == "https://ui.example"
                )
                document = client.get("/openapi.json").json()
                assert (
                    "multipart/form-data"
                    in document["paths"]["/__web_test/upload"]["post"]["requestBody"]["content"]
                )
                with client.stream("GET", "/__web_test/stream") as response:
                    assert next(response.iter_bytes()) == b"first\n"
                deadline = time.monotonic() + 5
                while client.get("/__web_test/info").json()["data"]["active_streams"]:
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
                for encoding in ("identity", "gzip"):
                    before = client.get(
                        "/__web_test/stream?before=true&sse=false&integrity=true",
                        headers={"Accept-Encoding": encoding},
                    )
                    assert before.json()["code"] == 500
                    if engine == "uvicorn":
                        with pytest.raises(httpx.RemoteProtocolError):
                            client.get(
                                "/__web_test/stream?fail=true&sse=false",
                                headers={"Accept-Encoding": encoding},
                            )
                    else:
                        with pytest.raises(
                            (httpx.RemoteProtocolError, httpx.ReadTimeout, ValueError)
                        ):
                            read_completed_stream(
                                client,
                                "/__web_test/stream?fail=true&sse=false&integrity=true",
                                {"Accept-Encoding": encoding},
                            )
                length_errors = (
                    (httpx.RemoteProtocolError, httpx.ReadTimeout)
                    if engine == "granian"
                    else (httpx.RemoteProtocolError,)
                )
                with pytest.raises(length_errors):
                    client.get("/__web_test/stream?fail=true&declared_length=true")
                raw = client.get("/__web_test/stream?sse=false")
                if engine == "granian":
                    assert raw.json()["code"] == 500
                else:
                    assert raw.content.endswith(b"done\n")
                assert len(list(evidence.glob("stream-closed-*"))) == (
                    6 if engine == "granian" else 7
                )
                client.post("/__stop")
                assert process.wait(timeout=10) == 0, log_path.read_text(encoding="utf-8")
                successful = True
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    assert successful
    assert json.loads((evidence / "resource-closed.json").read_text()) == {"active_streams": 0}
    assert json.loads((evidence / "host-closed.json").read_text()) == {
        "ready": False,
        "di_released": True,
        "definitions_released": True,
        "logging_closed": True,
    }
    log = log_path.read_text(encoding="utf-8")
    assert "HTTP-stream-secret" not in log
    assert "HTTP-stream-before-secret" not in log
    assert "Application callable raised an exception" not in log
    assert "Exception in ASGI application" not in log
    assert "outcome=disconnected" in log
    faults = [line for line in log.splitlines() if re.search(r"\|\s*ERROR\s*\|", line)]
    assert len(faults) == (6 if engine == "granian" else 5)
    assert len({re.search(r"request=([a-f0-9]+)", line).group(1) for line in faults}) == len(faults)
    assert "HTTP GET" in log


@pytest.mark.smoke
@pytest.mark.parametrize("engine", ["uvicorn", "granian"])
def test_cli_discovers_and_serves_web_module(engine, config_dir, module_package, tmp_path):
    module_package(
        "web_cli",
        files={
            "endpoints.py": r"""
from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.streaming_result import StreamingResult
from framework.starter_web.response.stream_integrity import StreamIntegrity
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy

@controller('/cli-module', policy=RoutePolicy.public())
class Endpoints:
    @route('/{value}')
    def read(self, value: int, request: Request):
        context = RequestContext.current()
        return {'value': value, 'same_app': context.connection.app is request.app, 'engine': request.app.state.web_stream_policy.engine}
    @route('/upload', methods=('POST',))
    async def write(self, request: Request):
        return {'bytes': sum([len(chunk) async for chunk in request.stream()])}

@controller('/cli-stream', policy=RoutePolicy.public())
class StreamEndpoints:
    @route('/raw', response_class=StreamingResponse)
    async def raw(self):
        async def chunks():
            yield b'raw'
        return StreamingResult(chunks())
    @route('/known', response_class=StreamingResponse)
    async def known(self, request: Request):
        return FileResult(request.app.state.bootstrap.response_settings).stream_bytes(b'known', 'data.bin')
    @route('/events', response_class=EventSourceResponse)
    async def events(self):
        yield ServerSentEvent(event='done', data={'count': 0})
    @route('/framed', response_class=StreamingResponse)
    @StreamIntegrity(protocol='cli-v1', completion_marker='DONE')
    async def framed(self):
        async def chunks():
            yield b'value\n'
            yield b'DONE'
        return StreamingResult(chunks())
"""
        },
    )
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    configuration = config_dir(
        {
            "server": {"port": port, "reload": False},
            engine: {"workers": 1},
            "modules": {"packages": ["framework", "web_cli"], "enabled": ["framework", "web_cli"]},
        }
    )
    environment = dict(
        os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8"
    )
    environment["PYTHONPATH"] = os.pathsep.join([str(tmp_path), str(ROOT / "dushan-admin-backend")])
    log_path = tmp_path / f"cli-{engine}.log"
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with log_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(ROOT / "dushan-admin-backend/app.py"),
                "--server",
                engine,
                "--env",
                "test",
                "--config-dir",
                str(configuration),
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            **options,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False
            ) as client:
                deadline = time.monotonic() + 20
                while True:
                    assert process.poll() is None, log_path.read_text(encoding="utf-8")
                    try:
                        response = client.get("/cli-module/7")
                        if response.status_code == 200:
                            break
                    except (httpx.NetworkError, httpx.TimeoutException):
                        pass
                    assert time.monotonic() < deadline, log_path.read_text(encoding="utf-8")
                    time.sleep(0.05)
                assert response.json() == {"value": 7, "same_app": True, "engine": engine}
                assert client.get("/cli-module/wrong").json()["code"] == 422
                assert client.post("/cli-module/upload", content=iter([b"a", b"bc"])).json() == {
                    "bytes": 3
                }
                assert "/cli-module/{value}" in client.get("/openapi.json").json()["paths"]
                raw = client.get("/cli-stream/raw")
                assert raw.json()["code"] == 500 if engine == "granian" else raw.content == b"raw"
                known = client.get("/cli-stream/known", headers={"Accept-Encoding": "gzip"})
                assert known.content == b"known"
                if engine == "granian":
                    assert known.headers["content-length"] == "5"
                    assert "content-encoding" not in known.headers
                assert "event: done" in client.get("/cli-stream/events").text
                assert client.get("/cli-stream/framed").content.endswith(b"DONE")
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                else:
                    import signal

                    os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
