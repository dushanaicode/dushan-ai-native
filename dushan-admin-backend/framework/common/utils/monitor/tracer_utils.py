from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from fastapi import Request
from opentelemetry.trace import Span

from framework.common.utils.trace.trace_context_utils import TraceAttributes, TraceContextUtils


class TracerUtils:
    """为请求读取稳定追踪 ID，并为自定义 Span 统一处理脱敏异常。"""

    @staticmethod
    def generate_trace_id() -> str:
        """显式创建 32 位十六进制本地标识。"""
        return uuid4().hex

    @classmethod
    def get_trace_id(cls, request: Request | None = None) -> str | None:
        """优先使用当前 Span；请求无远端链路时只创建并缓存一次本地标识。"""
        current = TraceContextUtils.get_current_trace_info()["trace_id"]
        if current is not None:
            return current
        if request is None:
            return None
        state = request.scope.setdefault("state", {})
        if "trace_id" not in state:
            remote = TraceContextUtils.extract_trace_from_request(request)["trace_id"]
            state["trace_id"] = cls.generate_trace_id() if remote is None else remote
        return state["trace_id"]

    @staticmethod
    def get_span_id() -> str | None:
        """返回当前真实 Span 的标识，缺失时返回 None。"""
        return TraceContextUtils.get_current_trace_info()["span_id"]

    @staticmethod
    @contextmanager
    def custom_span(name: str, attributes: TraceAttributes | None = None) -> Iterator[Span]:
        """在 Span 内执行工作，脱敏记录异常后保留原异常继续传播。"""
        with TraceContextUtils.start_span(name, attributes) as span:
            try:
                yield span
            except Exception as exc:
                TraceContextUtils.record_error(span, exc)
                raise
