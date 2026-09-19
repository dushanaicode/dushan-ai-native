from datetime import datetime, timezone
from time import perf_counter

from loguru import logger

from framework.common.security import Sanitizer
from framework.starter_di.public import (
    DiTaskRunner,
)
from framework.starter_logging.public import (
    LogContext,
)
from framework.starter_web.public import (
    AccessLogPolicy,
    HttpObservation,
)
from module_infra.spi.logger.api_access_log_service_provider_adapter import (
    ApiAccessLogServiceProviderAdapter,
)


class InfraAccessLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        context = None
        status = 500
        start = perf_counter()
        began = datetime.now(timezone.utc).replace(tzinfo=None)

        async def observe(message):
            nonlocal context, status
            if message["type"] == "http.response.start":
                context = LogContext.current()
                status = message["status"]
            await send(message)

        await self.app(scope, receive, observe)
        policy = getattr(scope.get("endpoint"), AccessLogPolicy.ATTRIBUTE, None)
        if context is None or policy is not None and not policy.enabled:
            return
        app = scope["app"]
        application = app.state.application_context
        observation = HttpObservation.find(scope)
        headers = dict(scope["headers"])
        values = dict(
            trace_id=context.trace_id or context.request_id or "",
            user_id=int(context.account_id) if context.account_id is not None else None,
            user_type=2 if context.account_id is not None else 0,
            tenant_id=context.tenant_id,
            application_name="dushan-ai-native",
            request_method=scope["method"],
            request_url=scope["state"].get("web_route_template", scope["path"])[:255],
            request_params=None,
            response_body=None,
            user_ip=context.client_ip or "",
            user_agent=Sanitizer.sanitize_text(headers.get(b"user-agent", b"").decode("latin-1"))[
                :200
            ],
            operate_module=policy.operate_module if policy else "",
            operate_name=policy.operate_name if policy else "",
            operate_type=policy.operate_type.code
            if policy is not None and policy.operate_type is not None
            else 0,
            begin_time=began,
            end_time=datetime.now(timezone.utc).replace(tzinfo=None),
            duration=int((perf_counter() - start) * 1000),
            result_code=observation.business_code
            if observation is not None and observation.business_code is not None
            else status,
            result_msg="",
        )
        try:
            await application.container.get(DiTaskRunner).run_isolated(
                application.container.get(ApiAccessLogServiceProviderAdapter).write, values
            )
        except Exception as error:
            logger.error("访问日志写入失败: {}", type(error).__name__)
