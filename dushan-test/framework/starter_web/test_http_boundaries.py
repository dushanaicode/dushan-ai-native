import asyncio

import httpx
import pytest
from fastapi import BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.exception.reported_http_failure import ReportedHttpFailure
from framework.starter_web.files.local_files import LocalFiles
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.response.streaming_result import StreamingResult

pytestmark = pytest.mark.unit


def create_uvicorn_app(**kwargs):
    """本文件的原始流故障用例明确选择 Uvicorn 的传输契约。"""
    return create_public_app(engine="uvicorn", **kwargs)


def scope(path, *, method="GET", headers=(), client=("127.0.0.1", 30000)):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": list(headers),
        "client": client,
        "server": ("localhost", 80),
    }


async def empty_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


def test_native_responses_keep_protocol_and_background_tasks(config_dir, tmp_path):
    app = create_uvicorn_app(base_dir=config_dir(), environ={})
    file = tmp_path / "sample.bin"
    file.write_bytes(b"abcdef")
    result = FileResult(app.state.bootstrap.response_settings)
    local = LocalFiles(tmp_path, result)
    events = []

    @app.get("/json", response_model=Result[int])
    async def regular():
        return Result.success(7)

    @app.get("/file")
    async def download():
        return local.download("sample.bin", file_name="示例.bin")

    @app.get("/redirect")
    async def redirect():
        return RedirectResponse("/health")

    @app.get("/empty")
    @app.head("/empty")
    async def empty(status: int = 204):
        return Response(status_code=status, headers={"ETag": "test"})

    @app.get("/existing-error")
    async def existing_error():
        return JSONResponse({"reason": "protocol"}, status_code=409, headers={"Retry-After": "3"})

    @app.get("/failure")
    async def failure():
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer", "Retry-After": "2"})

    @app.get("/background")
    async def background(tasks: BackgroundTasks):
        async def complete():
            assert RequestContext.current().connection.app is app
            assert ApplicationContext.current() is app.state.application_context
            events.append("background")

        tasks.add_task(complete)
        return {"ok": True}

    with TestClient(app) as client:
        assert client.get("/json").json() == {"code": 0, "message": "ok", "data": 7, "error": None}
        download = client.get("/file", headers={"Range": "bytes=1-3"})
        assert download.status_code == 206 and download.content == b"bcd"
        assert download.headers["content-range"] == "bytes 1-3/6"
        assert "filename*=UTF-8''" in download.headers["content-disposition"]
        assert client.get("/file", headers={"Range": "bytes=100-"}).status_code == 416
        assert client.get("/redirect", follow_redirects=False).status_code == 307
        for status in (204, 304):
            response = client.get(f"/empty?status={status}")
            assert response.status_code == status and response.content == b""
            assert response.headers["etag"] == "test"
        assert client.head("/empty").content == b""
        assert all(
            "content" not in item
            for item in client.get("/openapi.json")
            .json()["paths"]["/empty"]["head"]["responses"]
            .values()
        )
        response = client.get("/existing-error")
        assert response.status_code == 409 and response.json() == {"reason": "protocol"}
        assert response.headers["retry-after"] == "3"
        response = client.get("/failure")
        assert response.status_code == 200 and response.json()["code"] == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.headers["retry-after"] == "2"
        client.get("/background")
    assert events == ["background"]


@pytest.mark.parametrize(
    "method,status", [("HEAD", 200), ("HEAD", 400), ("GET", 204), ("GET", 304)]
)
async def test_bodyless_asgi_messages(config_dir, method, status):
    app = create_uvicorn_app(base_dir=config_dir(), environ={})
    app.add_api_route(
        "/bodyless", lambda: Response("illegal body", status_code=status), methods=[method]
    )
    sent = []

    async def send(message):
        sent.append(message)

    async with app.router.lifespan_context(app):
        await app(scope("/bodyless", method=method), empty_receive, send)
    assert len([m for m in sent if m["type"] == "http.response.start"]) == 1
    assert not b"".join(m.get("body", b"") for m in sent)


async def test_streaming_request_is_not_preconsumed_and_bytes_are_limited(config_dir):
    app = create_uvicorn_app(base_dir=config_dir({"web": {"max_body_bytes": 6}}), environ={})
    consumed = 0

    @app.post("/stream-in")
    async def stream_in(request: Request):
        assert consumed == 0
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
        return {"size": size}

    async def post(chunks):
        nonlocal consumed
        consumed = 0
        messages = iter(chunks)
        sent = []

        async def receive():
            nonlocal consumed
            consumed += 1
            return next(messages)

        async def send(message):
            sent.append(message)

        await app(scope("/stream-in", method="POST"), receive, send)
        return httpx.Response(sent[0]["status"], content=b"".join(m.get("body", b"") for m in sent))

    async with app.router.lifespan_context(app):
        good = await post(
            [
                {"type": "http.request", "body": b"abc", "more_body": True},
                {"type": "http.request", "body": b"def", "more_body": False},
            ]
        )
        assert good.json() == {"size": 6} and consumed == 2
        bad = await post(
            [
                {"type": "http.request", "body": b"abc", "more_body": True},
                {"type": "http.request", "body": b"defg", "more_body": False},
            ]
        )
        assert bad.status_code == 200 and bad.json()["code"] == 413
        assert app.state.application_context.get_statistics()["executions"] == 0


@pytest.mark.parametrize("failure", ["error", "cancel", "disconnect"])
async def test_started_stream_failure_never_sends_second_response_and_releases(config_dir, failure):
    app = create_uvicorn_app(base_dir=config_dir(), environ={})
    closed = []
    sent = []

    @app.get("/stream")
    async def stream():
        async def chunks():
            try:
                assert RequestContext.current().connection.app is app
                yield b"first"
                if failure == "error":
                    raise ValueError("password=stream-secret")
                yield b"second"
            finally:
                assert ApplicationContext.current() is app.state.application_context
                closed.append(True)

        return StreamingResult(chunks())

    async def send(message):
        sent.append(message)
        if message["type"] == "http.response.body" and failure == "cancel":
            raise asyncio.CancelledError()
        if message["type"] == "http.response.body" and failure == "disconnect":
            raise OSError("client closed")

    async with app.router.lifespan_context(app):
        if failure == "error":
            with pytest.raises(ReportedHttpFailure):
                await app(scope("/stream"), empty_receive, send)
            assert all(
                message.get("more_body", True)
                for message in sent
                if message["type"] == "http.response.body"
            )
        elif failure == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await app(scope("/stream"), empty_receive, send)
        else:
            await app(scope("/stream"), empty_receive, send)
        assert app.state.application_context.get_statistics()["executions"] == 0
    assert closed == [True]
    assert len([m for m in sent if m["type"] == "http.response.start"]) == 1
    assert b"code" not in b"".join(m.get("body", b"") for m in sent)
    with pytest.raises(RuntimeError):
        RequestContext.current()


async def test_stream_dependency_background_and_expired_child_context(config_dir):
    app = create_uvicorn_app(base_dir=config_dir(), environ={})
    events = []
    release_child = asyncio.Event()
    child_task = None

    async def dependency():
        events.append("open")
        try:
            yield "active"
        finally:
            assert RequestContext.current().connection.app is app
            events.append("close")

    @app.get("/stream", dependencies=[Depends(dependency)])
    async def stream(tasks: BackgroundTasks):
        nonlocal child_task

        async def child():
            await release_child.wait()
            with pytest.raises(RuntimeError):
                RequestContext.current()

        async def background():
            assert RequestContext.current().connection.app is app
            events.append("background")

        async def chunks():
            assert "close" not in events
            yield "first"
            await asyncio.sleep(0)
            assert "close" not in events
            events.append("last")
            yield "last"

        child_task = asyncio.create_task(child())
        tasks.add_task(background)
        return StreamingResult(chunks())

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            assert (await client.get("/stream")).content == b"firstlast"
        release_child.set()
        await child_task
    assert events.index("open") < events.index("last") < events.index("close")
    assert "background" in events


def test_cors_gzip_ip_and_sensitive_logging(config_dir):
    app = create_uvicorn_app(
        base_dir=config_dir(
            {
                "web": {"cors_origins": ["https://ui.example"], "gzip_minimum_size": 100},
                "config": {"models": {"ip": {"trusted_proxy_cidrs": ["127.0.0.1/32"]}}},
            }
        ),
        environ={},
    )

    @app.get("/ip")
    async def ip(request: Request):
        context = RequestContext.current()
        assert context.client_ip == LogContext.current().client_ip
        return {"ip": context.client_ip, "scheme": request.url.scheme}

    @app.get("/large")
    async def large():
        return {"content": "a" * 2000}

    @app.get("/broken")
    async def broken():
        raise RuntimeError("password=hidden-token")

    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        headers = {
            "Origin": "https://ui.example",
            "X-Forwarded-For": "203.0.113.9",
            "X-Forwarded-Proto": "https",
        }
        assert client.get("/ip", headers=headers).json() == {"ip": "203.0.113.9", "scheme": "https"}
        preflight = client.options(
            "/ip", headers={"Origin": "https://ui.example", "Access-Control-Request-Method": "GET"}
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "https://ui.example"
        assert (
            client.options(
                "/ip",
                headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
            ).status_code
            == 400
        )
        failed = client.get("/broken", headers=headers)
        assert failed.json()["code"] == 500 and "hidden-token" not in failed.text
        assert failed.headers["access-control-allow-origin"] == "https://ui.example"
        assert client.get("/large").headers["content-encoding"] == "gzip"
    with TestClient(app, client=("198.51.100.8", 1234)) as client:
        assert client.get("/ip", headers=headers).json() == {"ip": "198.51.100.8", "scheme": "http"}


def test_local_files_reject_escape_links_and_filename_injection(config_dir, tmp_path):
    from pathlib import Path

    app = create_uvicorn_app(base_dir=config_dir(), environ={})
    root = tmp_path / "files"
    root.mkdir()
    (root / "good.txt").write_text("ok")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    files = LocalFiles(root, FileResult(app.state.bootstrap.response_settings))
    for value in ("../outside.txt", str(outside), "x:stream", "..\\outside.txt"):
        with pytest.raises(ValueError):
            files.download(value)
    for name in ("../bad.txt", "bad\r\nX-Injected: yes", "bad/name"):
        with pytest.raises(ValueError):
            files.download("good.txt", file_name=name)
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"系统不允许创建文件符号链接：{type(error).__name__}")
    with pytest.raises(ValueError):
        files.download("linked.txt")
    assert Path(files.download("good.txt").path) == (root / "good.txt").resolve()


async def test_concurrent_requests_and_applications_keep_contexts_separate(config_dir):
    root = config_dir()
    first = create_uvicorn_app(base_dir=root, environ={"SERVER_NAME": "first"})
    second = create_uvicorn_app(base_dir=root, environ={"SERVER_NAME": "second"})

    async def identity(request: Request):
        context = RequestContext.current()
        request_id = context.request_id
        await asyncio.sleep(0.005)
        assert RequestContext.current() is context
        assert LogContext.current().request_id == request_id
        assert ApplicationContext.current() is request.app.state.application_context
        return {"id": request_id, "name": request.app.title}

    for app in (first, second):
        app.add_api_route("/identity", identity)
    async with first.router.lifespan_context(first), second.router.lifespan_context(second):
        async with (
            httpx.AsyncClient(transport=httpx.ASGITransport(first), base_url="http://one") as a,
            httpx.AsyncClient(transport=httpx.ASGITransport(second), base_url="http://two") as b,
        ):
            results = await asyncio.gather(*(client.get("/identity") for client in [a, b] * 5))
    assert len({response.json()["id"] for response in results}) == 10
    assert [response.json()["name"] for response in results] == ["first", "second"] * 5
    with pytest.raises(RuntimeError):
        RequestContext.current()


def test_access_logs_never_capture_payloads_and_respect_route_policy(config_dir, capsys):
    from framework.starter_web.routing.access_log_policy import AccessLogPolicy

    app = create_uvicorn_app(base_dir=config_dir(), environ={})

    @app.post("/public/{capability}")
    async def public(capability: str, body: dict):
        return {"ok": True}

    @app.get("/quiet")
    @AccessLogPolicy(enabled=False)
    async def quiet():
        return {"ok": True}

    with TestClient(app) as client:
        capsys.readouterr()
        client.post(
            "/public/path-capability-secret",
            json={"password": "body-password-secret"},
            headers={
                "Authorization": "Bearer header-token-secret",
                "Cookie": "session=cookie-secret",
            },
        )
        client.get("/quiet")
        output = capsys.readouterr().out
    assert "/public/{capability}" in output and "/quiet" not in output
    assert all(
        value not in output
        for value in (
            "path-capability-secret",
            "body-password-secret",
            "header-token-secret",
            "cookie-secret",
        )
    )


def test_access_log_retains_monitor_trace_after_span_finishes(config_dir, capsys):
    app = create_uvicorn_app(
        base_dir=config_dir(
            {
                "config": {
                    "models": {
                        "monitor": {"enabled": True, "exporter": "none", "sampler": "always_on"}
                    }
                }
            }
        ),
        environ={},
    )
    app.get("/traced")(lambda: {"ok": True})
    with TestClient(app) as client:
        capsys.readouterr()
        response = client.get("/traced")
        output = capsys.readouterr().out
        trace_id = response.headers["trace-id"]
    assert "HTTP GET /traced" in output
    assert f"trace={trace_id}" in output
