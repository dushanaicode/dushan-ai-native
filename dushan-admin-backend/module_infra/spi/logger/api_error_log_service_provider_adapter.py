import traceback
from datetime import datetime, timezone

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.security.sanitizer import Sanitizer
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject
from framework.starter_logging.context.log_context import LogContext
from framework.starter_security.config.security_settings import SecuritySettings
from module_infra.service.logger.api_error_log_service import ApiErrorLogService
from module_infra.spi.logger.dto.api_error_log_create_req_dto import ApiErrorLogCreateReqDTO


@framework
class ApiErrorLogServiceProviderAdapter:
    service: ApiErrorLogService = Inject()
    settings: SecuritySettings = Inject()
    tasks: DiTaskRunner = Inject()

    async def write(self, request, error, code, message):
        context = LogContext.current()
        frames = traceback.extract_tb(error.__traceback__)
        frame = frames[-1] if frames else None
        dto = ApiErrorLogCreateReqDTO(
            user_id=int(context.account_id) if context.account_id is not None else None,
            user_type=2 if context.account_id is not None else 0,
            tenant_id=context.tenant_id,
            application_name=self.settings.application_id,
            request_method=request.method,
            request_url=request.scope.get("state", {}).get("web_route_template", request.url.path)[
                :255
            ],
            request_params={},
            user_ip=context.client_ip or "",
            user_agent=request.headers.get("user-agent", "")[:200],
            exception_time=datetime.now(timezone.utc).replace(tzinfo=None),
            exception_name=type(error).__name__,
            exception_message=Sanitizer.sanitize_text(message)[:512],
            exception_root_cause_message="",
            exception_stack_trace="".join(ExceptionTraceFormatter.format(error)),
            exception_class_name=type(error).__module__,
            exception_file_name=frame.filename[-255:] if frame else "",
            exception_method_name=frame.name[:255] if frame else "",
            exception_line_number=frame.lineno if frame else 0,
            trace_id=context.trace_id or context.request_id or "",
        )
        await self.tasks.run_isolated(self.service.create_api_error_log, dto)
