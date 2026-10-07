from datetime import datetime, timezone
from time import perf_counter

from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.context.log_context import LogContext
from framework.starter_web.context.access_log_record import AccessLogRecord
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.access_log_policy import AccessLogPolicy
from framework.starter_web.routing.operate_type_enum import OperateTypeEnum
from framework.starter_web.spi.access_log_provider import AccessLogProvider


class AccessLogMiddleware:
    """请求完成后，通过启动阶段绑定的提供者写入访问元数据。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = scope["app"].state
        provider: AccessLogProvider | None = state.access_log_provider
        if provider is None:
            await self.app(scope, receive, send)
            return
        context = None
        status = 500
        start = perf_counter()
        began = datetime.now(timezone.utc).replace(tzinfo=None)

        async def observe(message: Message) -> None:
            nonlocal context, status
            if message["type"] == "http.response.start":
                context = LogContext.current()
                status = message["status"]
            await send(message)

        await self.app(scope, receive, observe)
        policy = getattr(scope.get("endpoint"), AccessLogPolicy.ATTRIBUTE, None)
        if context is None or policy is not None and not policy.enabled:
            return
        observation = HttpObservation.find(scope)
        request = RequestContext.current()
        record = AccessLogRecord(
            trace_id=context.trace_id or context.request_id or "",
            account_id=context.account_id,
            tenant_id=context.tenant_id,
            method=scope["method"],
            route=scope["state"].get("web_route_template", scope["path"])[:255],
            client_ip=request.client_ip_text,
            user_agent=Sanitizer.sanitize_text(request.user_agent)[:200],
            operate_module=policy.operate_module if policy else "",
            operate_name=policy.operate_name if policy else "",
            operate_type=(
                policy.operate_type
                if policy is not None and policy.operate_type is not None
                else OperateTypeEnum.from_method(scope["method"])
            ).code,
            begin_time=began,
            end_time=datetime.now(timezone.utc).replace(tzinfo=None),
            duration_ms=int((perf_counter() - start) * 1000),
            result_code=observation.business_code
            if observation is not None and observation.business_code is not None
            else status,
        )
        try:
            await state.access_log_tasks.run_isolated(provider.write, record)
        except Exception as error:
            logger.error("访问日志写入失败: {}", type(error).__name__)
