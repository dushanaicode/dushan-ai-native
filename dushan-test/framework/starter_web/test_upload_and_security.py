import asyncio
import tempfile
from typing import Annotated

import pytest
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from fixtures.public_web_app import create_public_app
from framework.common.security.field_mask import (
    DesensitizedApiKey,
    DesensitizedBankCard,
    DesensitizedCarLicense,
    DesensitizedChineseName,
    DesensitizedEmail,
    DesensitizedFixedPhone,
    DesensitizedIdCard,
    DesensitizedMobile,
    DesensitizedPassword,
)
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.router_registration import RouterRegistration
from framework.starter_web.security.rich_text_sanitizer import RichTextSanitizer

pytestmark = pytest.mark.unit


@pytest.fixture
def tracked_files(monkeypatch, tmp_path):
    import starlette.formparsers

    files = []

    def spool(*args, **kwargs):
        file = tempfile.SpooledTemporaryFile(*args, **kwargs, dir=tmp_path)
        files.append(file)
        return file

    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", spool)
    return files


def test_upload_native_binding_spool_boundary_and_cleanup(config_dir, tracked_files):
    app = create_public_app(
        base_dir=config_dir({"web": {"max_multipart_bytes": 2_000_000}}), environ={}
    )

    @app.post("/upload")
    async def upload(file: Annotated[UploadFile, File()], label: Annotated[str, Form()]):
        assert RequestContext.current().connection.app is app
        return {"size": file.size, "rolled": file.file._rolled, "label": label}

    with TestClient(app) as client:
        response = client.post(
            "/upload",
            files={"file": ("../../do-not-use-name.bin", b"a" * 1_100_000)},
            data={"label": "ok"},
        )
        assert response.json() == {"size": 1_100_000, "rolled": True, "label": "ok"}
        assert all(file.closed for file in tracked_files)
        too_large = client.post(
            "/upload", files={"file": ("big.bin", b"a" * 2_000_001)}, data={"label": "ok"}
        )
        assert too_large.status_code == 200 and too_large.json()["code"] == 413
        assert all(file.closed for file in tracked_files)
        invalid = client.post("/upload", files={"file": ("file.bin", b"a")})
        assert invalid.json()["code"] == 422 and all(file.closed for file in tracked_files)
        doc = client.get("/openapi.json").json()
        assert "multipart/form-data" in doc["paths"]["/upload"]["post"]["requestBody"]["content"]


@pytest.mark.parametrize("ending", ["cancel", "disconnect", "limit", "truncated"])
@pytest.mark.parametrize("entry", ["file", "form", "manual"])
async def test_partial_upload_files_close_on_every_exit(config_dir, tracked_files, ending, entry):
    router = APIRouter()

    if entry == "file":

        @router.post("/upload")
        async def upload(file: Annotated[UploadFile, File()]):
            pytest.fail("不完整或超限上传不能进入端点")
    elif entry == "form":

        @router.post("/upload")
        async def upload(label: Annotated[str, Form()]):
            pytest.fail("不完整或超限表单不能进入端点")
    else:

        @router.post("/upload")
        async def upload(request: Request):
            await request.form()
            pytest.fail("不完整或超限表单不能解析成功")

    app = create_public_app(
        base_dir=config_dir({"web": {"max_multipart_bytes": 512}}),
        environ={},
        routers=[RouterRegistration(router)],
    )

    prefix = b'--test\r\nContent-Disposition: form-data; name="file"; filename="data.bin"\r\nContent-Type: application/octet-stream\r\n\r\nabc'
    consumed = 0

    async def receive():
        nonlocal consumed
        consumed += 1
        if consumed == 1:
            return {"type": "http.request", "body": prefix, "more_body": True}
        assert tracked_files
        if ending == "cancel":
            raise asyncio.CancelledError()
        if ending == "disconnect":
            return {"type": "http.disconnect"}
        return {
            "type": "http.request",
            "body": b"a" * 600 if ending == "limit" else b"",
            "more_body": False,
        }

    messages = []

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"multipart/form-data; boundary=test")],
        "client": ("127.0.0.1", 40000),
        "server": ("localhost", 80),
    }
    async with app.router.lifespan_context(app):
        if ending == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await app(scope, receive, send)
        else:
            await app(scope, receive, send)
        assert app.state.application_context.get_statistics()["executions"] == 0
    assert tracked_files and all(file.closed for file in tracked_files)
    assert len([message for message in messages if message["type"] == "http.response.start"]) <= 1


@pytest.mark.parametrize(
    "annotation,value,expected",
    [
        (DesensitizedApiKey, "1234567890abcdef", "1234********cdef"),
        (DesensitizedApiKey, "short", "*****"),
        (DesensitizedMobile, "13812345678", "138****5678"),
        (DesensitizedBankCard, "123456789012", "123456****12"),
        (DesensitizedIdCard, "123456789012", "123456****12"),
        (DesensitizedCarLicense, "京A12345", "京A1***5"),
        (DesensitizedChineseName, "张三", "张*"),
        (DesensitizedFixedPhone, "01012345678", "0101*****78"),
        (DesensitizedPassword, "secret", "******"),
        (DesensitizedEmail, "alice@example.com", "a****@example.com"),
        (DesensitizedEmail, "invalid", "****"),
    ],
)
def test_explicit_field_masks_keep_original_values(annotation, value, expected):
    adapter = TypeAdapter(annotation)
    parsed = adapter.validate_python(value)
    assert parsed == value
    assert adapter.dump_python(parsed) == expected
    assert adapter.dump_json(parsed).decode() == '"' + expected + '"'


def test_rich_text_uses_explicit_html_allowlist():
    value = '<script>alert(1)</script><p style="color:red;position:absolute" onclick="bad()">ok</p><a href="javascript:alert(1)">link</a><img src="data:image/svg+xml;base64,AAAA" onerror="bad()">'
    cleaned = RichTextSanitizer.clean(value)
    assert "<script" not in cleaned
    assert "onclick" not in cleaned and "onerror" not in cleaned
    assert "javascript:" not in cleaned and "svg+xml" not in cleaned
    assert "position" not in cleaned and "color:red" in cleaned
    assert RichTextSanitizer.clean("<b>bold</b>") == "bold"
    assert '<img src="data:image/png;base64,AAAA">' == RichTextSanitizer.clean(
        '<img src="data:image/png;base64,AAAA">'
    )


def test_invisible_scheme_and_data_link_are_removed():
    for scheme in ("javascript\u200b", "java\nscript", "javascript", "data"):
        cleaned = RichTextSanitizer.clean(f'<a href="{scheme}:alert(1)">link</a>')
        assert "href=" not in cleaned


def test_explicit_upload_router_gets_safe_native_route_class(config_dir):
    from fastapi import APIRouter

    from framework.starter_web.routing.router_registration import RouterRegistration
    from framework.starter_web.routing.web_route import WebRoute

    async def upload(file: Annotated[UploadFile, File()]):
        return {"size": file.size}

    raw = APIRouter()
    raw.add_api_route("/upload", upload, methods=["POST"])
    app = create_public_app(base_dir=config_dir(), environ={}, routers=[RouterRegistration(raw)])
    with TestClient(app) as client:
        assert client.post("/upload", files={"file": ("a.bin", b"abc")}).json() == {"size": 3}
        assert all(isinstance(route, WebRoute) for route in app.routes if route.path == "/upload")
    safe = APIRouter(route_class=WebRoute)
    safe.add_api_route("/upload", upload, methods=["POST"])
    app = create_public_app(base_dir=config_dir(), environ={}, routers=[RouterRegistration(safe)])
    with TestClient(app) as client:
        assert client.post("/upload", files={"file": ("a.bin", b"abc")}).json() == {"size": 3}


async def test_cleanup_failure_keeps_cancellation_and_closes_remaining_files():
    from starlette.datastructures import Headers

    from framework.starter_web.upload.multipart_parser import MultipartParser

    closed = []

    class BrokenFile:
        def close(self):
            raise OSError("close failed")

    class GoodFile:
        def close(self):
            closed.append(True)

    async def stream():
        raise asyncio.CancelledError()
        yield b""

    parser = MultipartParser(
        Headers({"content-type": "multipart/form-data; boundary=test"}), stream()
    )
    parser._files_to_close_on_error = [BrokenFile(), GoodFile()]
    with pytest.raises(asyncio.CancelledError) as result:
        await parser.parse()
    assert closed == [True]
    assert isinstance(result.value.__cause__, BaseExceptionGroup)
    assert isinstance(result.value.__cause__.exceptions[0], OSError)
