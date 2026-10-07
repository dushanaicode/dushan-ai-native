from typing import override

from framework.starter_di.public import (
    DiTaskRunner,
    Inject,
    service,
)
from framework.starter_security.public import (
    SecuritySettings,
)
from framework.starter_web.context.error_log_record import ErrorLogRecord
from framework.starter_web.spi.error_log_provider import ErrorLogProvider
from module_infra.service.logger.api_error_log_service import ApiErrorLogService
from module_infra.spi.logger.dto.api_error_log_create_req_dto import ApiErrorLogCreateReqDTO


@service(interface=ErrorLogProvider)
class ApiErrorLogServiceProviderAdapter(ErrorLogProvider):
    service: ApiErrorLogService = Inject()
    settings: SecuritySettings = Inject()
    tasks: DiTaskRunner = Inject()

    @override
    async def write(self, record: ErrorLogRecord) -> None:
        """将框架错误事实映射为业务日志，并在独立执行域内持久化。"""
        dto = ApiErrorLogCreateReqDTO(
            user_id=int(record.account_id) if record.account_id is not None else None,
            user_type=2 if record.account_id is not None else 0,
            tenant_id=record.tenant_id,
            application_name=self.settings.application_id,
            request_method=record.method,
            request_url=record.route,
            request_params={},
            user_ip=record.client_ip,
            user_agent=record.user_agent,
            exception_time=record.exception_time,
            exception_name=record.exception_name,
            exception_message=record.exception_message,
            exception_root_cause_message="",
            exception_stack_trace=record.exception_stack_trace,
            exception_class_name=record.exception_class_name,
            exception_file_name=record.exception_file_name,
            exception_method_name=record.exception_method_name,
            exception_line_number=record.exception_line_number,
            trace_id=record.trace_id,
        )
        await self.tasks.run_isolated(self.service.create_api_error_log, dto)
