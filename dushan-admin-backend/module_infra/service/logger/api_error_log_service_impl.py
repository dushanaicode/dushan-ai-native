from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_tenant.config.tenant_settings import TenantSettings
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.dal.dataobject.logger.api_error_log_do import ApiErrorLogDO
from module_infra.dal.mapper.logger.api_error_log_mapper import ApiErrorLogMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.logger.api_error_log_process_status_enum import (
    ApiErrorLogProcessStatusEnum,
)
from module_infra.service.logger.api_error_log_service import ApiErrorLogService
from module_system.api.auth.workload_api import WorkloadApi


@service(interface=ApiErrorLogService)
class ApiErrorLogServiceImpl(ApiErrorLogService):
    api_error_log_mapper: ApiErrorLogMapper = Inject()
    date_utils: DateUtils = Inject()

    async def create_api_error_log(self, request):
        values = request.model_dump(by_alias=False)
        tenant_id = values.pop("tenant_id") or self.tenant_settings.default_tenant_id
        values["user_id"] = request.user_id
        values["user_type"] = request.user_type if request.user_type is not None else 0
        async with self.workloads.scope("infra.log.write", tenant_id):
            with self.database.scope():
                await self.api_error_log_mapper.insert(ApiErrorLogDO(**values))

    @override
    async def get_api_error_log_page(
        self, page_req_vo: ApiErrorLogPageReqVO
    ) -> PageResult[ApiErrorLogDO]:
        return await self.api_error_log_mapper.select_page(page_req_vo)

    @override
    async def update_api_error_log_process(
        self, log_id: int, process_status: int, process_user_id: int | None
    ) -> None:
        """更新 API 错误日志的处理状态"""
        error_log = await self.api_error_log_mapper.select_by_id(log_id)
        if error_log is None:
            raise ServiceException(ErrorCodeConstants.API_ERROR_LOG_NOT_FOUND)
        if error_log.process_status != ApiErrorLogProcessStatusEnum.INIT.code:
            raise ServiceException(ErrorCodeConstants.API_ERROR_LOG_PROCESSED)
        update_obj = ApiErrorLogDO(
            id=log_id,
            process_status=process_status,
            process_user_id=process_user_id,
            process_time=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await self.api_error_log_mapper.update_by_id(update_obj)

    @override
    async def clean_error_log(self, exceed_day: int, delete_limit: int) -> int:
        count = 0
        expire_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=exceed_day)
        while True:
            delete_count = await self.api_error_log_mapper.delete_by_create_time_lt(
                expire_date, delete_limit
            )
            count += delete_count
            if delete_count < delete_limit:
                break
        return count

    workloads: WorkloadApi = Inject()
    tenant_settings: TenantSettings = Inject()
    database: SessionProvider = Inject()
