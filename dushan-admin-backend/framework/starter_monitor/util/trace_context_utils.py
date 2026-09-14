from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import TypeVar

from fastapi import Request
from opentelemetry import context, trace
from opentelemetry.context import Context
from opentelemetry.trace import Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.core.monitor_span import MonitorSpan
from framework.starter_monitor.util.trace_info import TraceInfo

T = TypeVar("T")
type TraceAttributes = Mapping[str, str | bool | int | float]


class TraceContextUtils:
    """按 W3C traceparent 传播链路，直接依赖已声明的 OpenTelemetry API。"""

    @staticmethod
    def _info(span: Span) -> TraceInfo:
        """从有效 SpanContext 提取标准十六进制标识。"""
        span_context = span.get_span_context()
        if not span_context.is_valid:
            return {"trace_id": None, "span_id": None, "is_sampled": False}
        return {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
            "is_sampled": span_context.trace_flags.sampled,
        }

    @classmethod
    def get_current_trace_info(cls) -> TraceInfo:
        """读取当前链路信息，不为缺失链路伪造随机 ID。"""
        return cls._info(trace.get_current_span())

    @classmethod
    def extract_trace_from_request(cls, request: Request) -> TraceInfo:
        """只解析标准 W3C 头，不把任意客户端字符串作为追踪标识。"""
        extracted = TraceContextTextMapPropagator().extract(
            dict(request.headers), context=Context()
        )
        return cls._info(trace.get_current_span(extracted))

    @staticmethod
    def inject_trace_to_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
        """将当前 W3C 上下文写入请求头，并保留调用方其他头。"""
        result = {} if headers is None else headers
        TraceContextTextMapPropagator().inject(result)
        return result

    @staticmethod
    def save_context() -> Context:
        """取得当前上下文快照供显式传递。"""
        return context.get_current()

    @staticmethod
    def execute_with_context(
        saved_context: Context, func: Callable[..., T], *args: object, **kwargs: object
    ) -> T:
        """在同步调用期间绑定链路，无论成功失败均恢复上下文。"""
        token = context.attach(saved_context)
        try:
            return func(*args, **kwargs)
        finally:
            context.detach(token)

    @staticmethod
    async def execute_async_with_context(
        saved_context: Context, func: Callable[..., Awaitable[T]], *args: object, **kwargs: object
    ) -> T:
        """在异步调用期间绑定链路，取消时也恢复上下文。"""
        token = context.attach(saved_context)
        try:
            return await func(*args, **kwargs)
        finally:
            context.detach(token)

    @staticmethod
    def record_error(
        span: Span, exception: BaseException, attributes: TraceAttributes | None = None
    ) -> None:
        """复用应用安全 Span 的异常投影；不向裸 SDK Span 交付原始异常。"""
        if not span.is_recording():
            return
        if not isinstance(span, MonitorSpan):
            raise TypeError("异常记录必须使用 MonitorService 返回的安全 Span")
        span.record_exception(exception, attributes=attributes)

    @staticmethod
    def start_span(
        name: str, attributes: TraceAttributes | None = None
    ) -> AbstractContextManager[Span]:
        """通过当前应用开启 Span；未装配监控时无操作，失败由 MonitorService 统一记录。"""
        monitor = MonitorService.current()
        return (
            nullcontext(trace.INVALID_SPAN) if monitor is None else monitor.span(name, attributes)
        )
