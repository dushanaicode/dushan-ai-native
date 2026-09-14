import asyncio
from time import perf_counter
from uuid import uuid4

from loguru import logger
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.access_log_policy import AccessLogPolicy
from framework.starter_web.routing.operate_type_enum import OperateTypeEnum


class RequestContextMiddleware:
    """完整响应及后台回调共享请求归属；访问日志只记录协议计数和路由模板。"""

    def __init__(self, app: ASGIApp, access_log_enabled: bool) -> None:
        self.app = app
        self.access_log_enabled = access_log_enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        connection = HTTPConnection(scope)
        peer = connection.client.host if connection.client is not None else None
        proxies = connection.app.state.web_trusted_proxies
        client_ip = ClientIpResolver.resolve_client_ip(connection.headers, peer, proxies)
        scope["scheme"] = ClientIpResolver.resolve_request_scheme(
            connection.headers, peer, proxies, scope["scheme"]
        )
        request_id = uuid4().hex
        connection.state.client_ip = client_ip
        connection.state.request_id = request_id
        observation = HttpObservation()
        scope["state"][HttpObservation.KEY] = observation
        token = LogContext.begin_request(request_id)
        LogContext.set_client_ip(client_ip)
        started_at = perf_counter()

        async def observed_receive() -> Message:
            message = await receive()
            if message["type"] == "http.disconnect" and not observation.complete:
                observation.disconnected = True
            return message

        async def observed_send(message: Message) -> None:
            await send(message)
            if message["type"] == "http.response.start":
                observation.status = message["status"]
            elif message["type"] == "http.response.body":
                if scope["method"] != "HEAD" and observation.status not in {204, 304}:
                    observation.body_bytes += len(message.get("body", b""))
                observation.complete = not message.get("more_body", False)
            elif message["type"] == "http.response.pathsend":
                observation.complete = True

        try:
            with (
                logger.contextualize(logging_owner=connection.app.state.web_logging_owner),
                RequestContext.bind(connection, request_id, client_ip),
            ):
                try:
                    await self.app(scope, observed_receive, observed_send)
                except asyncio.CancelledError:
                    observation.cancelled = True
                    raise
                except Exception:
                    observation.failed = True
                    raise
                finally:
                    policy = getattr(scope.get("endpoint"), AccessLogPolicy.ATTRIBUTE, None)
                    if self.access_log_enabled and (policy is None or policy.enabled):
                        route = scope.get("route")
                        path = scope["state"].get(
                            "web_route_template", route.path if route is not None else "<unmatched>"
                        )
                        method = (
                            scope["method"]
                            if scope["method"]
                            in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"}
                            else "OTHER"
                        )
                        state = scope["state"]
                        trace_token = LogContext.bind_trace(
                            state.get("trace_id"), state.get("span_id")
                        )
                        try:
                            logger.info(
                                "HTTP {} {} status={} business_code={} bytes={} duration_ms={:.2f} outcome={} operation={}/{}/{}",
                                method,
                                path,
                                observation.status,
                                observation.business_code,
                                observation.body_bytes,
                                (perf_counter() - started_at) * 1000,
                                observation.outcome,
                                policy.operate_module if policy else "",
                                policy.operate_name if policy else "",
                                (
                                    policy.operate_type
                                    if policy and policy.operate_type is not None
                                    else OperateTypeEnum.from_method(method)
                                ).code,
                            )
                        finally:
                            LogContext.reset(trace_token)
        finally:
            LogContext.reset(token)
