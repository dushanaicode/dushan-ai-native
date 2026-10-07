import hashlib
import io

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from fixtures.config_factory import ConfigFactory
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.streaming_result import StreamingResult

pytestmark = pytest.mark.unit


def _response(files, method, tmp_path, **options):
    """通过三种真实文件入口复用同一组响应策略断言。"""
    if method == "download":
        path = tmp_path / "source.bin"
        path.write_bytes(b"abc")
        return files.download(path, "image.png", **options)
    return getattr(files, method)(b"abc", "image.png", **options)


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    ("media_type", "expected"),
    [
        ("image/png", "inline"),
        ("image/jpeg", "inline"),
        ("image/gif", "inline"),
        ("image/webp", "inline"),
        ("image/avif", "inline"),
        ("image/svg+xml", "attachment"),
        ("text/html", "attachment"),
        ("application/pdf", "attachment"),
        ("application/octet-stream", "attachment"),
    ],
)
def test_inline_requires_safe_raster_media_type(method, media_type, expected, tmp_path):
    """仅白名单栅格图片可内联，文件扩展名不能放宽类型限制。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    response = _response(files, method, tmp_path, media_type=media_type, disposition="inline")
    assert response.headers["content-disposition"].startswith(f"{expected};")


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    ("attachment", "media_type", "disposition", "expected"),
    [
        (False, "image/png", None, "inline"),
        (False, "text/plain", None, "attachment"),
        (True, "image/png", None, "attachment"),
        (False, "image/png", "attachment", "attachment"),
    ],
)
def test_disposition_defaults_and_explicit_override(
    method, attachment, media_type, disposition, expected, tmp_path
):
    """未指定时继承应用配置，显式附件策略与安全白名单优先。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response", attachment=attachment))
    response = _response(files, method, tmp_path, media_type=media_type, disposition=disposition)
    assert response.headers["content-disposition"].startswith(f"{expected};")


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    ("name", "expected_type", "expected_disposition"),
    [
        ("image.png", "image/png", "inline"),
        ("page.html", "text/html", "attachment"),
        ("unknown.file-response-headers", "application/octet-stream", "attachment"),
    ],
)
def test_missing_media_type_is_inferred_from_display_name(
    method, name, expected_type, expected_disposition, tmp_path
):
    """所有入口按显示文件名推断类型，未知类型使用二进制附件。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    content = b"abc"
    if method == "download":
        content = tmp_path / "source.bin"
        content.write_bytes(b"abc")
    response = getattr(files, method)(content, name, disposition="inline")
    assert response.media_type == expected_type
    assert response.headers["content-disposition"].startswith(f"{expected_disposition};")


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"cache": "no-store"}, "no-store"),
        ({"cache": "private"}, "private, max-age=60"),
        ({"cache": "public"}, "public, max-age=60"),
        ({"cache": "public", "max_age": 0}, "public, max-age=0"),
        (
            {"cache": "public", "max_age": 86400, "immutable": True},
            "public, max-age=86400, immutable",
        ),
    ],
)
def test_per_call_cache_and_default_security_headers(method, options, expected, tmp_path):
    """调用级缓存覆盖应用默认值，所有文件入口携带固定安全头。"""
    files = FileResult(
        ConfigFactory.build(
            ResponseSettings, "response", download_cache="private", download_max_age=60
        )
    )
    response = _response(files, method, tmp_path, **options)
    assert response.headers["cache-control"] == expected
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    ("cache", "expected"),
    [
        ("no-store", "no-store"),
        ("private", "private, max-age=60"),
        ("public", "public, max-age=60"),
    ],
)
def test_explicit_and_default_cache_have_same_meaning(method, cache, expected, tmp_path):
    """显式缓存参数与应用级缓存配置使用相同语义。"""
    files = FileResult(
        ConfigFactory.build(ResponseSettings, "response", download_cache=cache, download_max_age=60)
    )
    assert _response(files, method, tmp_path).headers["cache-control"] == expected
    assert _response(files, method, tmp_path, cache=cache).headers["cache-control"] == expected


def test_public_defaults_allow_per_call_max_age_and_immutable():
    """应用已启用公开缓存时可直接指定调用级时长与不可变标志。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response", download_cache="public"))
    response = files.from_bytes(b"abc", "file.bin", max_age=120, immutable=True)
    assert response.headers["cache-control"] == "public, max-age=120, immutable"


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    "options",
    [
        {"cache": "private", "max_age": 60},
        {"cache": "no-store", "immutable": True},
        {"max_age": 60},
        {"immutable": True},
    ],
)
def test_cache_rejects_unused_public_options(method, options, tmp_path):
    """非公开缓存不能指定公开缓存专用选项。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response", download_cache="no-store"))
    with pytest.raises(ValueError):
        _response(files, method, tmp_path, **options)


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
@pytest.mark.parametrize(
    "header",
    [
        "Content-Type",
        "Content-Disposition",
        "Cache-Control",
        "ETag",
        "X-Content-Type-Options",
        "Content-Security-Policy",
    ],
)
@pytest.mark.parametrize("uppercase", [False, True])
def test_managed_headers_reject_case_insensitive_conflicts(method, header, uppercase, tmp_path):
    """调用方不能通过任意大小写头字段绕过文件策略。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    key = header.upper() if uppercase else header.lower()
    with pytest.raises(ValueError):
        _response(
            files,
            method,
            tmp_path,
            media_type="image/png",
            disposition="inline",
            headers={key: "text/html"},
        )


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes", "download"])
def test_unmanaged_headers_are_preserved_without_mutating_input(method, tmp_path):
    """自定义头保留原值且不修改调用方持有的字典。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    headers = {"X-Export": "ready", "Access-Control-Expose-Headers": "ETag"}
    response = _response(files, method, tmp_path, headers=headers)
    assert response.headers["x-export"] == "ready"
    assert response.headers["access-control-expose-headers"] == "ETag, Content-Disposition"
    assert headers == {"X-Export": "ready", "Access-Control-Expose-Headers": "ETag"}


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes"])
@pytest.mark.parametrize("cache", ["private", "public"])
@pytest.mark.parametrize("match", ["exact", "weak", "list", "wildcard"])
def test_conditional_memory_response_has_same_policy_and_no_body(method, cache, match):
    """真实 HTTP 条件请求支持弱标签和列表，304 保留缓存安全头且不声明正文。"""
    content = b"abc"
    etag = f'"{hashlib.sha256(content).hexdigest()}"'
    condition = {
        "exact": etag,
        "weak": f"W/{etag}",
        "list": f'"different", W/{etag}',
        "wildcard": "*",
    }[match]
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    app = FastAPI()

    @app.get("/file")
    async def file():
        """以同一文件及策略验证正常响应和条件响应。"""
        return getattr(files, method)(
            content,
            "image.png",
            "image/png",
            disposition="inline",
            cache=cache,
            headers={"Content-Length": str(len(content)), "X-Export": "ready"},
        )

    with TestClient(app) as client:
        normal = client.get("/file")
        cached = client.get("/file", headers={"If-None-Match": condition})
        stale = client.get("/file", headers={"If-None-Match": '"different"'})
    assert normal.status_code == stale.status_code == 200
    assert normal.content == stale.content == content
    assert normal.headers["etag"] == etag
    assert cached.status_code == 304 and cached.content == b""
    assert "content-length" not in cached.headers
    assert "content-type" not in cached.headers
    for key in (
        "etag",
        "cache-control",
        "content-disposition",
        "x-content-type-options",
        "content-security-policy",
        "x-export",
    ):
        assert cached.headers[key] == normal.headers[key]


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes"])
@pytest.mark.parametrize(
    "http_method,expected_status,expected_content",
    [("HEAD", 304, b""), ("POST", 200, b"abc")],
)
def test_conditional_file_response_only_applies_to_reads(
    method, http_method, expected_status, expected_content
):
    """HEAD 可命中条件读取，POST 导出不会被改成 304。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    app = FastAPI()

    @app.api_route("/file", methods=["HEAD", "POST"])
    async def file():
        """发送可缓存内容，检查条件读取的方法边界。"""
        return getattr(files, method)(b"abc", "file.bin", cache="private")

    with TestClient(app) as client:
        response = client.request(http_method, "/file", headers={"If-None-Match": "*"})
    assert response.status_code == expected_status
    assert response.content == expected_content


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes"])
@pytest.mark.parametrize("conditional", [False, True])
def test_conditional_bytesio_preserves_cursor_and_releases_view(method, conditional):
    """发送 200 或 304 都保留缓冲区游标及所有权，并释放内存视图。"""
    buffer = io.BytesIO(b"abc")
    buffer.seek(1)
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    etag = f'"{hashlib.sha256(b"abc").hexdigest()}"'
    response = getattr(files, method)(buffer, "data.bin", cache="public")
    assert response.status_code == 200
    assert response.headers["etag"] == etag
    if method == "stream_bytes":
        assert isinstance(response, StreamingResult)
    else:
        assert response.body == b"abc"
    app = FastAPI()

    @app.get("/file")
    async def file():
        """条件读取在响应发送时决定，不需要路由接收请求对象。"""
        return response

    with TestClient(app) as client:
        sent = client.get("/file", headers={"If-None-Match": etag} if conditional else {})
    assert sent.status_code == (304 if conditional else 200)
    assert sent.content == (b"" if conditional else b"abc")
    assert buffer.tell() == 1 and not buffer.closed
    buffer.seek(0, io.SEEK_END)
    buffer.write(b"more")
    assert buffer.getvalue() == b"abcmore"


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes"])
@pytest.mark.parametrize("explicit", [False, True])
def test_no_store_skips_etag_hashing_and_conditional_requests(method, explicit, monkeypatch):
    """显式和默认 no-store 都不哈希内容，携带条件头仍返回完整正文。"""
    files = FileResult(
        ConfigFactory.build(
            ResponseSettings, "response", download_cache="private" if explicit else "no-store"
        )
    )

    def unexpected_hash(*args, **kwargs):
        """任何内容哈希都会使本用例失败。"""
        pytest.fail("no-store 不应计算 ETag")

    monkeypatch.setattr(
        "framework.starter_web.response.file_result.hashlib.sha256", unexpected_hash
    )
    app = FastAPI()

    @app.get("/file")
    async def file():
        """用应用策略或调用参数生成禁止缓存的响应。"""
        return getattr(files, method)(b"abc", "file.bin", cache="no-store" if explicit else None)

    with TestClient(app) as client:
        response = client.get("/file", headers={"If-None-Match": "*"})
    assert response.status_code == 200 and response.content == b"abc"
    assert response.headers["cache-control"] == "no-store"
    assert "etag" not in response.headers


@pytest.mark.parametrize("method", ["from_bytes", "stream_bytes"])
def test_conditional_response_runs_background_tasks(method):
    """304 沿用原文件响应的后台任务，且只执行一次。"""
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    events = []
    app = FastAPI()

    @app.get("/file")
    async def file(tasks: BackgroundTasks):
        """在 FastAPI 挂接后台任务后再由响应处理条件读取。"""
        tasks.add_task(events.append, "sent")
        return getattr(files, method)(b"abc", "file.bin", cache="private")

    with TestClient(app) as client:
        response = client.get("/file", headers={"If-None-Match": "*"})
    assert response.status_code == 304
    assert events == ["sent"]


def test_disk_download_infers_raster_type_and_keeps_native_etag(tmp_path):
    """磁盘下载按显示文件名推断类型，ETag 仍由原生 FileResponse 生成。"""
    path = tmp_path / "stored.bin"
    path.write_bytes(b"abc")
    files = FileResult(ConfigFactory.build(ResponseSettings, "response"))
    app = FastAPI()

    @app.get("/file")
    async def file():
        """发送磁盘内容并保留原生文件条件处理。"""
        return files.download(path, "image.png", disposition="inline")

    response = files.download(path, "image.png", disposition="inline")
    assert response.media_type == "image/png"
    assert "etag" not in response.headers
    with TestClient(app) as client:
        downloaded = client.get("/file")
    assert downloaded.status_code == 200 and downloaded.content == b"abc"
    assert downloaded.headers["content-disposition"].startswith("inline;")
    assert "etag" in downloaded.headers
