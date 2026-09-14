import io

import pytest
from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.stream_integrity import StreamIntegrity
from framework.starter_web.response.streaming_result import StreamingResult


@pytest.mark.parametrize("engine", ["granian", "uvicorn"])
@pytest.mark.parametrize("media_type", ["application/octet-stream", "text/event-stream"])
def test_raw_stream_admission_precedes_iteration(config_dir, engine, media_type):
    app = create_public_app(base_dir=config_dir(), environ={}, engine=engine)
    iterations = []

    @app.get("/raw", response_class=StreamingResponse)
    async def raw():
        async def chunks():
            iterations.append("started")
            yield b"raw"

        return StreamingResponse(chunks(), media_type=media_type)

    with TestClient(app) as client:
        response = client.get("/raw")
        assert app.state.web_stream_policy.engine == engine
        if engine == "granian":
            assert response.json()["code"] == 500
            assert iterations == []
            assert "content-encoding" not in response.headers
        else:
            assert response.content == b"raw" and iterations == ["started"]


@pytest.mark.parametrize("engine", ["granian", "uvicorn"])
def test_native_sse_and_integrity_declaration_remain_available(config_dir, engine):
    app = create_public_app(base_dir=config_dir(), environ={}, engine=engine)
    protocol = StreamIntegrity(protocol="export-v1", completion_marker="DONE")

    @app.get("/events", response_class=EventSourceResponse)
    async def events():
        yield ServerSentEvent(data={"value": 1}, event="item")
        yield ServerSentEvent(event="done", data={"count": 1})

    @app.get("/framed", response_class=StreamingResponse)
    @protocol
    async def framed():
        async def chunks():
            yield b"value\n"
            yield b"DONE"

        return StreamingResult(chunks(), integrity=protocol)

    with TestClient(app) as client:
        sse = client.get("/events")
        assert sse.headers["content-type"].startswith("text/event-stream")
        assert "event: item" in sse.text and "event: done" in sse.text
        assert "content-encoding" not in sse.headers
        framed = client.get("/framed")
        assert framed.content == b"value\nDONE"
        operation = app.openapi()["paths"]["/framed"]["get"]
        assert operation["x-stream-integrity"] == {
            "protocol": "export-v1",
            "completion_marker": "DONE",
        }


@pytest.mark.parametrize("entry", ["stream_bytes", "excel_stream", "file"])
def test_granian_known_length_survives_gzip_negotiation(config_dir, tmp_path, entry):
    app = create_public_app(base_dir=config_dir(), environ={}, engine="granian")
    payload = b"known" * 100_000
    buffer = io.BytesIO(payload)
    buffer.seek(9)
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)

    @app.get("/known")
    async def known(request: Request):
        files = FileResult(request.app.state.bootstrap.response_settings)
        if entry == "file":
            return files.download(path)
        return getattr(files, entry)(buffer, "payload.bin")

    with TestClient(app) as client:
        response = client.get("/known", headers={"Accept-Encoding": "gzip"})
        assert response.content == payload
        assert response.headers["content-length"] == str(len(payload))
        assert "content-encoding" not in response.headers
    assert buffer.tell() == 9 and not buffer.closed


def test_stream_bytes_rejects_false_length(config_dir):
    app = create_public_app(base_dir=config_dir(), environ={}, engine="granian")
    files = FileResult(app.state.bootstrap.response_settings)
    with pytest.raises(ValueError, match="长度不一致"):
        files.stream_bytes(b"123", "a.bin", headers={"Content-Length": "4"})
    assert files.stream_bytes(b"", "a.bin").headers["content-length"] == "0"


def test_rejecting_prepared_generator_releases_its_resource(config_dir):
    app = create_public_app(base_dir=config_dir(), environ={}, engine="granian")
    events = []

    @app.get("/already-prepared")
    async def prepared():
        async def chunks():
            events.append("open")
            try:
                yield b"prepared"
                yield b"next"
            finally:
                events.append("closed")

        source = chunks()
        await anext(source)
        return StreamingResponse(source)

    with TestClient(app) as client:
        assert client.get("/already-prepared").json()["code"] == 500
    assert events == ["open", "closed"]


def test_explicit_embedding_engine_overrides_yaml_and_environment(config_dir):
    root = config_dir({"server": {"engine": "granian"}})
    first = create_public_app(base_dir=root, environ={"SERVER_ENGINE": "granian"}, engine="uvicorn")
    second = create_public_app(
        base_dir=root, environ={"SERVER_ENGINE": "uvicorn"}, engine="granian"
    )
    with TestClient(first), TestClient(second):
        assert first.state.web_stream_policy.engine == "uvicorn"
        assert second.state.web_stream_policy.engine == "granian"
        assert first.state.web_stream_policy is not second.state.web_stream_policy
