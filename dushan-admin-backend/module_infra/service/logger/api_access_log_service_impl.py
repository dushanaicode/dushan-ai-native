from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.dates import DateUtils
from framework.common.page import PageResult
from framework.starter_database.public import (
    SessionProvider,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from module_infra.controller.admin.logger.vo.apiaccesslog.apiaccesslog_api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_access_log_do import ApiAccessLogDO
from module_infra.dal.mapper.logger.api_access_log_mapper import ApiAccessLogMapper
from module_infra.service.logger.api_access_log_service import ApiAccessLogService
from module_system.api.auth.workload_api import WorkloadApi


@service(interface=ApiAccessLogService)
class ApiAccessLogServiceImpl(ApiAccessLogService):
    api_access_log_mapper: ApiAccessLogMapper = Inject()
    date_utils: DateUtils = Inject()

    async def create_api_access_log(self, request):
        values = request.model_dump(by_alias=False)
        tenant_id = values.pop("tenant_id") or self.tenant_settings.default_tenant_id
        values["user_id"] = request.user_id
        values["user_type"] = request.user_type if request.user_type is not None else 0
        async with self.workloads.scope("infra.log.write", tenant_id):
            with self.database.scope():
                await self.api_access_log_mapper.insert(ApiAccessLogDO(**values))

    @override
    async def get_api_access_log_page(
        self, page_req_vo: ApiAccessLogPageReqVO
    ) -> PageResult[ApiAccessLogDO]:
        return await self.api_access_log_mapper.select_page(page_req_vo)

    @override
    async def clean_access_log(self, exceed_day: int, delete_limit: int) -> int:
        count = 0
        expire_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=exceed_day)
        while True:
            delete_count = await self.api_access_log_mapper.delete_by_create_time_lt(
                expire_date, delete_limit
            )
            count += delete_count
            if delete_count < delete_limit:
                break
        return count

    workloads: WorkloadApi = Inject()
    tenant_settings: TenantSettings = Inject()
    database: SessionProvider = Inject()
