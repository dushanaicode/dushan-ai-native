from opentelemetry.trace import SpanKind
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class MonitorMiddleware:
    """单个纯ASGI服务端Span覆盖完整响应；不采集请求体、原始URL、头或Cookie。"""

    METHODS = frozenset(
        {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
    )

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        monitor = scope["app"].state.monitor
        if monitor is None:
            await self.app(scope, receive, send)
            return
        settings = monitor.settings
        if (
            not settings.enabled
            or not settings.http_enabled
            or scope["path"] in settings.excluded_paths
        ):
            with monitor.bind():
                await self.app(scope, receive, send)
            return
        method = scope["method"] if scope["method"] in self.METHODS else "_OTHER"
        parent = monitor.extract(scope["headers"])
        with monitor.span(
            f"HTTP {method}", {"http.request.method": method}, kind=SpanKind.SERVER, parent=parent
        ) as span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                scope.setdefault("state", {})["trace_id"] = format(span_context.trace_id, "032x")
                scope["state"]["span_id"] = format(span_context.span_id, "016x")

            async def traced_send(message: Message):
                if message["type"] == "http.response.start":
                    monitor._observe(
                        span.set_attribute, "http.response.status_code", message["status"]
                    )
                    if message["status"] >= 500:
                        from opentelemetry.trace import StatusCode

                        monitor._observe(span.set_status, StatusCode.ERROR)
                    if settings.response_trace_header and span_context.is_valid:
                        headers = [
                            (key, value)
                            for key, value in message.get("headers", ())
                            if key.lower() != b"trace-id"
                        ]
                        headers.append(
                            (b"trace-id", format(span_context.trace_id, "032x").encode("ascii"))
                        )
                        message = {**message, "headers": headers}
                await send(message)

            try:
                await self.app(scope, receive, traced_send)
            finally:
                monitor._observe(self._record_route, span, scope, method)

    @staticmethod
    def _record_route(span, scope, method):
        route = scope.get("route")
        if route is not None:
            span.set_attribute("http.route", route.path)
            span.update_name(f"{method} {route.path}")
