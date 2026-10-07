from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import SecuritySettings
from framework.starter_web.context.access_log_record import AccessLogRecord
from framework.starter_web.spi.access_log_provider import AccessLogProvider
from module_infra.service.logger.api_access_log_service import ApiAccessLogService
from module_infra.spi.logger.dto.api_access_log_create_req_dto import ApiAccessLogCreateReqDTO


@service(interface=AccessLogProvider)
class ApiAccessLogServiceProviderAdapter(AccessLogProvider):
    service: ApiAccessLogService = Inject()
    settings: SecuritySettings = Inject()

    @override
    async def write(self, record: AccessLogRecord) -> None:
        """将请求事实映射为当前应用的访问日志。"""
        dto = ApiAccessLogCreateReqDTO(
            trace_id=record.trace_id,
            user_id=int(record.account_id) if record.account_id is not None else None,
            user_type=2 if record.account_id is not None else 0,
            tenant_id=record.tenant_id,
            application_name=self.settings.application_id,
            request_method=record.method,
            request_url=record.route,
            request_params=None,
            response_body=None,
            user_ip=record.client_ip,
            user_agent=record.user_agent,
            operate_module=record.operate_module,
            operate_name=record.operate_name,
            operate_type=record.operate_type,
            begin_time=record.begin_time,
            end_time=record.end_time,
            duration=record.duration_ms,
            result_code=record.result_code,
            result_msg="",
        )
        await self.service.create_api_access_log(dto)
