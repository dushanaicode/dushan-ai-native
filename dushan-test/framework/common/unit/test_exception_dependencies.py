from asyncio import CancelledError
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from loguru import logger

from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.exceptions.rate_limit_exception import RateLimitException
from framework.starter_web.exception.error_log_recorder import ErrorLogRecorder
from framework.starter_web.exception.exception_handler import GlobalExceptionHandler
from framework.starter_web.exception.exception_logger import ExceptionLogger
from framework.starter_web.exception.response_builder import ExceptionResponseBuilder

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "level", [level for level in LogLevelEnum if level is not LogLevelEnum.NONE]
)
def test_exception_enum_levels_reach_loguru_with_safe_trace_threshold(level: LogLevelEnum) -> None:
    """七个有效级别正确进入 Loguru，只有 ERROR 及以上附带脱敏异常链。"""

    class ClassifiedException(BaseBusinessException):
        log_level = level

    try:
        raise RuntimeError("password=private-cause")
    except RuntimeError as cause:
        exc = ClassifiedException(
            GlobalErrorCodeConstants.BAD_REQUEST,
            msg="处理失败 token=private-message",
            cause=cause,
        )
    messages = []
    sink = logger.add(messages.append, level=LogLevelEnum.TRACE.value, format="{message}")
    try:
        ExceptionLogger.log(exc, exc.error_code, exc.msg, "/records")
    finally:
        logger.remove(sink)
    assert len(messages) == 1
    assert messages[0].record["level"].name == level.value
    assert "业务异常" in messages[0]
    assert "private-message" not in messages[0] and "private-cause" not in messages[0]
    if level in (LogLevelEnum.ERROR, LogLevelEnum.CRITICAL):
        assert "RuntimeError" in messages[0] and "password=***" in messages[0]
        assert "\nTraceback (most recent call last):\n" in messages[0]
        assert "\nRuntimeError: password=***\n" in messages[0]
    else:
        assert "RuntimeError" not in messages[0]


def test_unclassified_system_exception_keeps_error_level_and_safe_trace() -> None:
    """普通系统异常继续记录为 ERROR，不受业务异常默认级别影响。"""
    messages = []
    sink = logger.add(messages.append, level=LogLevelEnum.TRACE.value, format="{message}")
    try:
        ExceptionLogger.log(
            RuntimeError("password=private-system"),
            GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR,
            "服务异常",
            "/records",
        )
    finally:
        logger.remove(sink)
    assert len(messages) == 1
    assert messages[0].record["level"].name == LogLevelEnum.ERROR.value
    assert "系统异常" in messages[0] and "RuntimeError" in messages[0]
    assert "\nRuntimeError: password=***\n" in messages[0]
    assert "private-system" not in messages[0]


async def test_error_log_recorder_uses_injected_writer() -> None:
    """实例记录器把原异常与公开信息交给注入的写入函数。"""
    records: list[tuple[object, Exception, ErrorCode, str]] = []

    async def write(request, exc, error_code, msg) -> None:
        """记录四个位置参数，供断言依赖边界。"""
        records.append((request, exc, error_code, msg))

    request = Request({"type": "http"})
    original = RuntimeError("failed")
    definition = GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
    await ErrorLogRecorder(write).record(request, original, definition, "系统异常")
    assert records == [(request, original, definition, "系统异常")]


def test_exception_response_builder_sanitizes_debug_payload() -> None:
    """显式调试响应中的提示、上下文和原始异常都经过脱敏。"""
    exc = BaseBusinessException(
        ErrorCode(code=4999, description="debug failure", message_key="debug.failure"),
        msg="failed token=abc",
        context={"access_token": "secret", "safe": "value"},
        cause=RuntimeError("password=secret"),
    )
    body = ExceptionResponseBuilder.build(exc.error_code, exc.msg, exc=exc, debug=True)
    assert body["message"] == "failed token=***"
    assert body["error"]["debug"]["context"]["access_token"] == "***"
    assert body["error"]["debug"]["context"]["safe"] == "value"
    assert "password=***" in body["error"]["debug"]["cause"]
    assert isinstance(body["error"]["debug"]["stacktrace"], list)
    assert "debug" not in ExceptionResponseBuilder.build(exc.error_code, exc.msg, exc=exc)


def test_response_builder_hides_internal_context_outside_debug_mode() -> None:
    """默认响应不包含原始异常、上下文或堆栈，只输出脱敏后的公开字段。"""
    definition = GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
    exc = BaseBusinessException(
        definition, context={"private": "internal-context"}, cause=RuntimeError("internal-cause")
    )

    body = ExceptionResponseBuilder.build(definition, exc.msg, exc=exc)

    assert set(body) == {"code", "message", "data", "error"}
    assert body["message"] == definition.description
    assert body["data"] is None
    assert "internal" not in repr(body)


async def test_error_log_recorder_ignores_write_failure_and_preserves_cancellation() -> None:
    """写入失败不会替换业务异常，任务取消仍继续传播。"""

    class FailingWriter:
        def __init__(self, failure: BaseException) -> None:
            """保存写入时触发的异常。"""
            self.failure = failure

        async def write(self, request, exc, error_code, msg) -> None:
            """触发模拟写入故障。"""
            raise self.failure

    arguments = (
        Request({"type": "http"}),
        RuntimeError("original"),
        GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR,
        "系统异常",
    )
    await ErrorLogRecorder(FailingWriter(RuntimeError("write failed")).write).record(*arguments)
    cancellation = CancelledError()
    with pytest.raises(CancelledError) as captured:
        await ErrorLogRecorder(FailingWriter(cancellation).write).record(*arguments)
    assert captured.value is cancellation


async def test_registered_exception_handlers_preserve_http_and_public_error_contracts() -> None:
    """真实 ASGI 请求保留状态和响应头，并隔离校验输入与内部异常详情。"""
    app = FastAPI()
    GlobalExceptionHandler().register(app)

    @app.get("/http-error")
    async def http_error() -> None:
        """触发带认证响应头的 HTTP 异常。"""
        raise HTTPException(
            status_code=401,
            detail="token=raw-http-secret",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/validated")
    async def validated(count: int) -> dict[str, int]:
        """通过整数查询参数触发请求校验。"""
        return {"count": count}

    @app.get("/rate-limit")
    async def rate_limit() -> None:
        """触发具有重试等待时间的限流异常。"""
        raise RateLimitException()

    @app.get("/internal-error")
    async def internal_error() -> None:
        """触发不得直接暴露给调用方的内部故障。"""
        raise RuntimeError("private-internal-cause")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/http-error")
        assert response.status_code == 200
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["code"] == 401
        assert response.json()["message"] == "token=***"

        response = await client.get("/validated", params={"count": "raw-validation-secret"})
        assert response.status_code == 200
        assert response.json()["code"] == 422
        assert response.json()["data"] is None
        assert response.json()["error"]["fields"] == [
            {"field": "count", "message": "值的类型不正确"}
        ]
        assert "raw-validation-secret" not in response.text

        response = await client.get("/rate-limit")
        assert response.status_code == 200
        assert response.headers["retry-after"] == "2"
        assert response.json()["code"] == 429
        assert response.json()["error"]["retryable"] is True
        assert response.json()["error"]["retryAfter"] == 2

        response = await client.get("/internal-error")
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 500
        assert body["message"] == GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR.description
        assert set(body) == {"code", "message", "data", "error"}
        assert "private-internal-cause" not in response.text


async def test_translated_logs_are_redacted_and_format_fallback_is_not_retranslated() -> None:
    """译文先脱敏再记录，格式失败的默认提示不被二次翻译覆盖。"""

    class Translator:
        def translate_any_scope(self, *args, **kwargs) -> str:
            """模拟包含敏感字段的翻译结果。"""
            return "password=private-translation"

    app = FastAPI()
    GlobalExceptionHandler(translator=Translator()).register(app)

    @app.get("/translated")
    async def translated() -> None:
        """触发经过翻译层处理的 HTTP 错误。"""
        raise HTTPException(status_code=404, detail="资源不存在")

    @app.get("/fallback")
    async def fallback() -> None:
        """触发格式错误，观察最终 HTTP 提示是否保留默认值。"""
        raise BaseBusinessException(
            GlobalErrorCodeConstants.BAD_REQUEST, msg="错误 {", format_args=("参数",)
        )

    messages: list[str] = []
    handler_id = logger.add(messages.append, format="{message}")
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            translated_response = await client.get("/translated")
            assert translated_response.status_code == 200
            assert translated_response.json()["message"] == "password=***"
            fallback_response = await client.get("/fallback")
            assert fallback_response.status_code == 200
            assert (
                fallback_response.json()["message"]
                == GlobalErrorCodeConstants.BAD_REQUEST.description
            )
    finally:
        logger.remove(handler_id)
    log_text = "".join(messages)
    assert messages
    assert "password=***" in log_text
    assert "private-translation" not in log_text


async def test_error_persistence_policy_for_5xx_and_explicit_record_error() -> None:
    """5xx（含 HTTPException）默认尝试入库，4xx 仅在显式开启 record_error 时入库。"""

    translated_keys: list[str] = []

    class RecordingTranslator:
        def translate_any_scope(self, message_key: str, language, **kwargs) -> str:
            """记录处理器查询的翻译键，并返回原有默认提示。"""
            translated_keys.append(message_key)
            return kwargs.get("default") or message_key

    class MemoryErrorLogService:
        def __init__(self) -> None:
            """收集本实例的诊断记录。"""
            self.records: list[dict[str, Any]] = []

        async def log_error(self, request, exc, error_code, msg) -> None:
            """接收实例记录器传入的位置参数。"""
            self.records.append(
                {
                    "request": request,
                    "exception": exc,
                    "result_code": error_code.code,
                    "result_msg": msg,
                }
            )

    service = MemoryErrorLogService()

    app = FastAPI()
    GlobalExceptionHandler(
        translator=RecordingTranslator(), error_recorder=ErrorLogRecorder(service.log_error)
    ).register(app)

    @app.get("/http-500")
    async def http_500() -> None:
        """触发应默认记录的内部 HTTP 错误。"""
        raise HTTPException(status_code=500, detail="gateway crash")

    @app.get("/http-503")
    async def http_503() -> None:
        """触发应默认记录的服务不可用错误。"""
        raise HTTPException(status_code=503, detail="service down")

    @app.get("/http-502")
    async def http_502() -> None:
        """触发上游网关故障，与本地配置错误分别分类。"""
        raise HTTPException(status_code=502, detail="upstream unavailable")

    @app.get("/http-400")
    async def http_400() -> None:
        """触发默认不记录的请求错误。"""
        raise HTTPException(status_code=400, detail="bad input")

    @app.get("/biz-400-default")
    async def biz_400_default() -> None:
        """触发默认不记录的业务请求错误。"""
        raise BaseBusinessException(GlobalErrorCodeConstants.BAD_REQUEST)

    @app.get("/biz-400-recorded")
    async def biz_400_recorded() -> None:
        """触发明确要求记录的业务请求错误。"""
        raise BaseBusinessException(GlobalErrorCodeConstants.BAD_REQUEST, record_error=True)

    @app.get("/biz-500-config")
    async def biz_500_config() -> None:
        """触发使用独立业务码的配置错误。"""
        raise ConfigurationException()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get("/http-500")
        assert res.status_code == 200
        assert len(service.records) == 1
        assert service.records[-1]["result_code"] == 500

        res = await client.get("/http-503")
        assert res.status_code == 200
        assert len(service.records) == 2
        assert service.records[-1]["result_code"] == 503

        res = await client.get("/http-400")
        assert res.status_code == 200
        assert len(service.records) == 2

        res = await client.get("/biz-400-default")
        assert res.status_code == 200
        assert len(service.records) == 2

        res = await client.get("/biz-400-recorded")
        assert res.status_code == 200
        assert len(service.records) == 3
        assert service.records[-1]["result_code"] == 400

        res = await client.get("/biz-500-config")
        assert res.status_code == 200
        assert res.json()["code"] == 502
        assert len(service.records) == 4
        assert service.records[-1]["result_code"] == 502
        assert translated_keys[-1] == "exception.error_configuration"

        res = await client.get("/http-502")
        assert res.status_code == 200
        assert res.json()["code"] == 903
        assert len(service.records) == 5
        assert service.records[-1]["result_code"] == 903
        assert translated_keys[-1] == "exception.bad_gateway"


async def test_http_exception_logs_5xx_as_error_and_4xx_as_warning() -> None:
    """HTTPException 5xx 按 ERROR 级别记录，4xx 按 WARNING 级别记录。"""
    app = FastAPI()
    GlobalExceptionHandler().register(app)

    @app.get("/err-500")
    async def err_500() -> None:
        """触发用于核对 ERROR 日志级别的 HTTP 错误。"""
        raise HTTPException(status_code=500, detail="internal fail")

    @app.get("/err-400")
    async def err_400() -> None:
        """触发用于核对 WARNING 日志级别的 HTTP 错误。"""
        raise HTTPException(status_code=400, detail="bad client request")

    messages: list[tuple[str, str]] = []
    handler_id = logger.add(
        lambda msg: messages.append((msg.record["level"].name, msg.record["message"])),
        level="DEBUG",
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.get("/err-500")
            await client.get("/err-400")
    finally:
        logger.remove(handler_id)

    levels = [lvl for lvl, _ in messages]
    assert "ERROR" in levels
    assert "WARNING" in levels
    error_msgs = [m for lvl, m in messages if lvl == "ERROR"]
    assert any("HTTP 服务端异常：500" in m for m in error_msgs)
    warn_msgs = [m for lvl, m in messages if lvl == "WARNING"]
    assert any("HTTP 客户端异常：400" in m for m in warn_msgs)


@pytest.mark.parametrize("first", ["a", "b"])
async def test_apps_keep_debug_translation_recording_and_tracing_independent(first: str) -> None:
    """两个应用交错注册和关闭时，各自的调试开关与注入依赖始终独立。"""

    class DependencySpy:
        def __init__(self, name: str) -> None:
            """分别记录本应用的翻译、写入和追踪调用。"""
            self.name = name
            self.translations: list[tuple[str, str | None]] = []
            self.records: list[tuple[Request, Exception, ErrorCode, str]] = []
            self.traces: list[Exception] = []

        def translate_any_scope(self, key, accept_language, *, default=None, args=None) -> str:
            """返回带应用标记的提示，暴露跨实例误用。"""
            self.translations.append((key, accept_language))
            return f"{self.name}:{default}"

        async def write(self, request, exc, error_code, msg) -> None:
            """保存当前应用收到的原异常与公开提示。"""
            self.records.append((request, exc, error_code, msg))

        def on_error(self, exc: Exception) -> None:
            """保存本应用收到的追踪事件。"""
            self.traces.append(exc)

    spies = {name: DependencySpy(name) for name in ("a", "b")}
    apps: dict[str, FastAPI] = {}

    def build_app(name: str) -> FastAPI:
        """构造具有独立异常依赖的最小应用。"""
        app = FastAPI()
        spy = spies[name]
        # 旧 app.state 槽位没有翻译能力；处理器必须只使用显式依赖。
        app.state.i18n_translator = object()
        GlobalExceptionHandler(
            spy, translator=spy, error_recorder=ErrorLogRecorder(spy.write), debug=name == "a"
        ).register(app)

        @app.get("/failure")
        async def failure() -> None:
            """抛出带敏感上下文的配置异常。"""
            raise ConfigurationException(
                context={"safe": name, "password": "private-context"},
                cause=RuntimeError("password=private-cause"),
            )

        return app

    second = "b" if first == "a" else "a"
    for name in (first, second):
        apps[name] = build_app(name)

    async def request_failure(name: str) -> None:
        """发出请求并核对当前应用的独立公开契约。"""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=apps[name]), base_url="http://test"
        ) as client:
            response = await client.get("/failure", headers={"Accept-Language": "en-US"})
        assert response.status_code == 200
        body = response.json()
        assert (
            body["message"] == f"{name}:{GlobalErrorCodeConstants.ERROR_CONFIGURATION.description}"
        )
        assert (body["error"] is not None and "debug" in body["error"]) is (name == "a")
        if name == "a":
            assert body["error"]["debug"]["context"] == {"safe": "a", "password": "***"}
        assert "private-context" not in response.text
        assert "private-cause" not in response.text

    async with apps[first].router.lifespan_context(apps[first]):
        async with apps[second].router.lifespan_context(apps[second]):
            await request_failure(first)
            await request_failure(second)
        await request_failure(first)

    for name, count in ((first, 2), (second, 1)):
        spy = spies[name]
        assert spy.translations == [("exception.error_configuration", "en-US")] * count
        assert len(spy.records) == len(spy.traces) == count
        for (request, exc, error_code, msg), trace in zip(spy.records, spy.traces, strict=True):
            assert request.app is apps[name]
            assert exc is trace
            assert error_code is GlobalErrorCodeConstants.ERROR_CONFIGURATION
            assert msg.startswith(f"{name}:")


async def test_405_logs_route_template_without_secret_path_segments() -> None:
    """方法不允许的请求保留路由模板与 Allow 头，日志不包含实际敏感路径。"""
    app = FastAPI()
    GlobalExceptionHandler().register(app)

    @app.get("/protected/{capability}")
    async def protected(capability: str) -> dict[str, bool]:
        """声明用于检查部分路由匹配的合法方法。"""
        return {"ok": True}

    messages: list[str] = []
    handler_id = logger.add(messages.append, format="{message}")
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/protected/private-capability")
    finally:
        logger.remove(handler_id)
    assert response.status_code == 200
    assert "GET" in response.headers["allow"]
    text = "".join(messages)
    assert messages
    assert "/protected/{capability}" in text
    assert "private-capability" not in text


async def test_dependency_failures_preserve_the_business_response() -> None:
    """翻译、追踪和记录依赖同时失效时，仍返回脱敏后的原业务错误。"""

    class FailingDependencies:
        def translate_any_scope(self, *args, **kwargs) -> str:
            """模拟翻译服务故障。"""
            raise ValueError("password=private-translation")

        def on_error(self, exc: Exception) -> None:
            """模拟追踪服务故障。"""
            raise RuntimeError("password=private-trace")

        async def write(self, request, exc, error_code, msg) -> None:
            """模拟记录服务故障。"""
            raise OSError("password=private-recorder")

    failing = FailingDependencies()
    app = FastAPI()
    GlobalExceptionHandler(
        failing, translator=failing, error_recorder=ErrorLogRecorder(failing.write)
    ).register(app)

    @app.get("/failure")
    async def failure() -> None:
        """触发默认需要记录的配置异常。"""
        raise ConfigurationException()

    messages: list[str] = []
    handler_id = logger.add(messages.append, format="{message}", level="DEBUG")
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/failure")
    finally:
        logger.remove(handler_id)
    assert response.status_code == 200
    assert response.json()["code"] == GlobalErrorCodeConstants.ERROR_CONFIGURATION.code
    assert response.json()["message"] == GlobalErrorCodeConstants.ERROR_CONFIGURATION.description
    log_text = "".join(messages)
    assert messages
    assert "password=***" in log_text
    assert "private-translation" not in log_text
    assert "private-trace" not in log_text
    assert "private-recorder" not in log_text
    for prefix in ("异常链路追踪记录失败", "异常文案翻译失败"):
        record = next(message for message in messages if prefix in message)
        assert "Traceback (most recent call last):\n" in record
        assert "password=***\n" in record
