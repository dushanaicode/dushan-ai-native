import asyncio
import io
import json
from datetime import datetime, timezone

import anyio
import pytest
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient
from loguru import logger
from pydantic import ValidationError
from starlette.requests import ClientDisconnect

from fixtures.config_factory import ConfigFactory
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.error_details import ErrorDetails
from framework.common.exception.core.field_error import FieldError
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.middleware_result import MiddlewareResult
from framework.starter_web.response.result import Result
from framework.starter_web.response.streaming_result import StreamingResult

pytestmark = pytest.mark.unit


def test_success_uses_one_public_contract_and_preserves_business_content():
    """成功体保留业务原文和 JSON 类型转换，拒绝未知参数和伪成功码。"""
    result = Result.success({"text": " keep ", "at": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    body = result.to_response()
    assert body["code"] == 0 and body["message"] == "ok"
    assert body["data"] == {"text": " keep ", "at": "2026-01-01T00:00:00Z"}
    assert set(body) == {"code", "message", "data", "error"}
    with pytest.raises(TypeError):
        Result.success(code=500)
    with pytest.raises(ValidationError):
        Result(code=True)


async def test_middleware_response_and_asgi_send_share_encoded_body_and_headers():
    """两条中间件路径输出相同字节，HTTP头、编码和脱敏不各自实现。"""
    middleware = MiddlewareResult()
    values = {1: datetime(2026, 1, 1, tzinfo=timezone.utc), "password": "private"}
    headers = {"WWW-Authenticate": "Bearer", "Retry-After": "3"}
    response = middleware.error_response(
        GlobalErrorCodeConstants.UNAUTHORIZED, data=values, headers=headers
    )
    messages = []

    async def send(message):
        messages.append(message)

    await middleware.send_error(
        send, GlobalErrorCodeConstants.UNAUTHORIZED, data=values, headers=headers
    )
    assert response.status_code == messages[0]["status"] == 200
    assert messages[0]["headers"] == response.raw_headers
    assert messages[1] == {"type": "http.response.body", "body": response.body, "more_body": False}
    assert json.loads(response.body)["data"] == {
        "1": "2026-01-01T00:00:00+00:00",
        "password": "***",
    }
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["retry-after"] == "3"
    assert middleware.error_response().status_code == 200
    assert (
        middleware.error_response(GlobalErrorCodeConstants.ERROR_CONFIGURATION).status_code == 200
    )
    assert middleware.error_response(GlobalErrorCodeConstants.BAD_GATEWAY).status_code == 200


@pytest.mark.parametrize(
    "vary,expected",
    [("Origin", "Origin, Accept-Language"), ("*", "*"), ("accept-language", "accept-language")],
)
def test_translation_is_instance_scoped_and_merges_vary(vary, expected):
    """显式传入语言和翻译器，不改变调用方的头字典或无翻译实例。"""

    class Translator:
        def translate_any_scope(self, key, accept_language, *, default=None, args=None):
            assert key == "exception.bad_request"
            return f"{accept_language}:{default}"

    middleware = MiddlewareResult(Translator())
    headers = {"Vary": vary}
    response = middleware.error_response(
        GlobalErrorCodeConstants.BAD_REQUEST, accept_language="en-US", headers=headers
    )
    assert json.loads(response.body)["message"].startswith("en-US:")
    assert response.headers["vary"] == expected
    assert headers == {"Vary": vary}
    assert "vary" not in MiddlewareResult().error_response().headers
    assert json.loads(middleware.error_response(message="final {}").body)["message"] == "final {}"


def test_translation_failure_and_debug_output_do_not_disclose_secrets():
    """翻译故障保留错误语义，调试输出仍脱敏且由实例明确开启。"""

    class BrokenTranslator:
        def translate_any_scope(self, *args, **kwargs):
            raise ValueError("password=private-translation")

    error = ConfigurationException(
        context={"token": "private-token"}, cause=RuntimeError("password=private-cause")
    )
    middleware = MiddlewareResult(BrokenTranslator(), debug=True)
    messages = []
    sink = logger.add(messages.append, format="{message}")
    try:
        body = middleware.error_response(
            GlobalErrorCodeConstants.ERROR_CONFIGURATION, exc=error
        ).body
    finally:
        logger.remove(sink)
    decoded = json.loads(body)
    assert decoded["message"] == GlobalErrorCodeConstants.ERROR_CONFIGURATION.description
    assert decoded["error"]["debug"]["context"] == {"token": "***"}
    assert isinstance(decoded["error"]["debug"]["stacktrace"], list)
    assert b"private-" not in body
    assert len(messages) == 1
    assert "Traceback (most recent call last):\n" in messages[0]
    assert "\nValueError: password=***\n" in messages[0]
    assert "private-translation" not in messages[0]
    assert json.loads(MiddlewareResult().error_response(exc=error).body)["error"] is None
    with pytest.raises(TypeError):
        MiddlewareResult(debug="false")


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("with_exception", [False, True])
def test_error_details_cannot_supply_debug_output(debug, with_exception):
    """输入详情不能夹带诊断，开启调试时也只使用构造器生成的脱敏内容。"""
    supplied = ErrorDetails(
        fields=(FieldError(field="name", message="名称不可用"),),
        debug={"internal_note": "untrusted-diagnostic"},
    )
    exc = ConfigurationException(context={"token": "private-token"}) if with_exception else None
    response = MiddlewareResult(debug=debug).error_response(error=supplied, exc=exc)
    details = json.loads(response.body)["error"]
    assert details["fields"] == [{"field": "name", "message": "名称不可用"}]
    assert b"untrusted-diagnostic" not in response.body
    if debug and with_exception:
        assert details["debug"]["exception_type"] == "ConfigurationException"
        assert details["debug"]["context"] == {"token": "***"}
    else:
        assert "debug" not in details
    assert supplied.debug == {"internal_note": "untrusted-diagnostic"}


@pytest.mark.parametrize(
    "error_code",
    [
        GlobalErrorCodeConstants.SUCCESS,
        ErrorCode(code=123, description="redirect", message_key="test.redirect", http_status=302),
    ],
)
def test_error_response_rejects_success_and_non_error_http_status(error_code):
    """错误响应入口不能误发成功码或重定向状态。"""
    with pytest.raises(ValueError):
        MiddlewareResult().error_response(error_code)


def test_memory_download_preserves_buffer_and_enforces_policy():
    """读取 BytesIO 不改变游标或所有权，文件名和缓存策略由当前实例决定。"""
    buffer = io.BytesIO(b"abcdef")
    buffer.seek(2)
    result = FileResult(ConfigFactory.build(ResponseSettings, "response", max_memory_bytes=6))
    response = result.from_bytes(
        buffer, "数据.csv", headers={"Access-Control-Expose-Headers": "ETag", "X-Export": "ready"}
    )
    assert response.body == b"abcdef"
    assert buffer.tell() == 2 and not buffer.closed
    assert response.headers["cache-control"] == "no-store"
    assert (
        response.headers["content-disposition"]
        == "attachment; filename*=UTF-8''%E6%95%B0%E6%8D%AE.csv"
    )
    assert response.headers["access-control-expose-headers"] == "ETag, Content-Disposition"
    assert response.headers["x-export"] == "ready"
    with pytest.raises(ValueError, match="内存下载超过"):
        FileResult(
            ConfigFactory.build(ResponseSettings, "response", max_memory_bytes=5)
        ).from_bytes(buffer, "data.csv")
    inline = FileResult(
        ConfigFactory.build(
            ResponseSettings,
            "response",
            attachment=False,
            download_cache="private",
            download_max_age=60,
        )
    ).from_bytes(b"x", "a.txt")
    assert inline.headers["cache-control"] == "private, max-age=60"
    assert inline.headers["content-disposition"].startswith("inline;")
    assert result.excel(b"sheet", "a.xlsx").media_type.endswith("spreadsheetml.sheet")


@pytest.mark.parametrize(
    "name", ["", ".", "..", "../private", "a\\b.csv", "a\r\nX-Test:x", "a\x00.csv"]
)
def test_download_filename_rejects_paths_and_control_characters(name):
    """显示文件名不能引入路径语义或响应头注入。"""
    with pytest.raises(ValueError, match="显示文件名"):
        FileResult(ConfigFactory.build(ResponseSettings, "response")).from_bytes(b"x", name)


def test_disk_download_uses_native_head_range_and_chunk_size(tmp_path):
    """真实 ASGI 请求验证标准文件响应的 Range、HEAD 与下载头。"""
    path = tmp_path / "data.bin"
    path.write_bytes(b"abcdef")
    files = FileResult(ConfigFactory.build(ResponseSettings, "response", file_chunk_size=2))
    response = files.download(path)
    assert response.chunk_size == 2
    app = FastAPI()

    @app.api_route("/download", methods=["GET", "HEAD"])
    async def download():
        return files.download(path)

    with TestClient(app) as client:
        head = client.head("/download")
        partial = client.get("/download", headers={"Range": "bytes=1-3"})
        invalid = client.get("/download", headers={"Range": "bytes=20-"})
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == "6"
    assert partial.status_code == 206 and partial.content == b"bcd"
    assert partial.headers["content-range"] == "bytes 1-3/6"
    assert partial.headers["cache-control"] == "no-store"
    assert invalid.status_code == 416
    with pytest.raises(FileNotFoundError):
        files.download(tmp_path / "absent")


@pytest.mark.parametrize(
    "options",
    [
        {"file_chunk_size": 0},
        {"max_memory_bytes": False},
        {"download_max_age": -1},
        {"download_cache": "invalid"},
    ],
)
def test_response_configuration_rejects_invalid_limits(options):
    """无效分块、内存和缓存策略在配置加载阶段失败。"""
    with pytest.raises(ValidationError):
        ConfigFactory.build(ResponseSettings, "response", **options)


async def test_excel_memory_stream_is_chunked_and_preserves_buffer_ownership():
    """内存文件分块发送不移动游标，断连后归还视图并保留原发送异常。"""
    buffer = io.BytesIO(b"abcdef")
    buffer.seek(2)
    files = FileResult(
        ConfigFactory.build(ResponseSettings, "response", file_chunk_size=2, max_memory_bytes=6)
    )
    messages = []

    async def send(message):
        messages.append(message)

    response = files.excel_stream(buffer, "data.xlsx")
    await response.stream_response(send)
    assert [message["body"] for message in messages if message["type"] == "http.response.body"] == [
        b"ab",
        b"cd",
        b"ef",
        b"",
    ]
    assert buffer.tell() == 2 and not buffer.closed
    original = OSError("disconnected")

    async def broken_send(message):
        if message["type"] == "http.response.body":
            raise original

    with pytest.raises(OSError) as caught:
        await files.excel_stream(buffer, "data.xlsx").stream_response(broken_send)
    assert caught.value is original
    buffer.write(b"x")
    assert buffer.tell() == 3
    with pytest.raises(ValueError, match="内存下载超过"):
        FileResult(
            ConfigFactory.build(ResponseSettings, "response", max_memory_bytes=2)
        ).stream_bytes(buffer, "large.txt")


async def test_stream_closes_generator_on_success_and_send_failure():
    """发送失败发生在 yield 之后时，也必须执行生成器的异步释放。"""
    released = []

    async def chunks():
        try:
            yield b"first"
            yield "后续"
        finally:
            await asyncio.sleep(0)
            released.append(True)

    messages = []

    async def send(message):
        messages.append(message)

    await StreamingResult(chunks()).stream_response(send)
    assert released == [True]
    assert b"".join(message.get("body", b"") for message in messages) == "first后续".encode()
    original = OSError("client disconnected")

    async def broken_send(message):
        if message["type"] == "http.response.body":
            raise original

    with pytest.raises(OSError) as captured:
        await StreamingResult(chunks()).stream_response(broken_send)
    assert captured.value is original and released == [True, True]


async def test_stream_cancellation_shields_async_close_without_swallowing_cancel():
    """AnyIO 取消已发生时，生成器在 yield 暂停点仍能异步释放。"""
    closed = []

    async def chunks():
        try:
            yield b"x"
        finally:
            await anyio.sleep(0)
            closed.append(True)

    async def send(message):
        if message["type"] == "http.response.body":
            scope.cancel()
            await anyio.sleep(0)

    with anyio.CancelScope() as scope:
        await StreamingResult(chunks()).stream_response(send)
        pytest.fail("取消信号必须继续传播")
    assert scope.cancelled_caught and closed == [True]


async def test_stream_preserves_original_error_when_close_also_fails():
    """清理失败以附注记录，不覆盖原始网络故障。"""

    async def chunks():
        try:
            yield b"x"
        finally:
            raise RuntimeError("cleanup failed")

    original = OSError("send failed")

    async def send(message):
        if message["type"] == "http.response.body":
            raise original

    with pytest.raises(OSError) as captured:
        await StreamingResult(chunks()).stream_response(send)
    assert captured.value is original
    assert original.__notes__ == ["响应流清理失败：RuntimeError"]


async def test_asgi_24_disconnect_closes_stream():
    """走完整响应调用时，由 Starlette 转换断连异常并保留资源释放。"""
    closed = []

    async def chunks():
        try:
            yield b"x"
        finally:
            closed.append(True)

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("closed")

    with pytest.raises(ClientDisconnect):
        await StreamingResult(chunks())(
            {"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send
        )
    assert closed == [True]


async def test_asgi_disconnect_during_generation_runs_resource_cleanup():
    """接收断连信号时，生成器自身保护内部 await 触发的异步资源释放。"""
    waiting = anyio.Event()
    closed = []

    async def chunks():
        try:
            yield b"first"
            waiting.set()
            await anyio.sleep_forever()
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.sleep(0)
                closed.append(True)

    async def receive():
        await waiting.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        pass

    with anyio.fail_after(2):
        await StreamingResult(chunks())(
            {"type": "http", "asgi": {"spec_version": "2.0"}}, receive, send
        )
    assert closed == [True]


def test_native_sse_route_encodes_structured_and_multiline_events():
    """使用当前 FastAPI 的公开 SSE 接口验证格式，避免手写拼接协议。"""
    app = FastAPI()

    @app.get("/events", response_class=EventSourceResponse)
    async def events():
        yield ServerSentEvent(data={"name": "渡山"}, event="ready", id="1")
        yield ServerSentEvent(raw_data="first\nsecond", retry=1000)

    with TestClient(app) as client:
        response = client.get("/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: ready\n" in response.text and "id: 1\n" in response.text
    assert "data: first\ndata: second\n" in response.text
    assert "retry: 1000\n" in response.text
    assert "connection" not in response.headers
    with pytest.raises(ValidationError):
        ServerSentEvent(id="1\ninjected")
