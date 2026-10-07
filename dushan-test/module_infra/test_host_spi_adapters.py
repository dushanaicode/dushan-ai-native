from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.starter_config.provider.config_change import ConfigChange
from framework.starter_config.provider.config_update_result import ConfigUpdateResult
from framework.starter_config.spi.config_source_provider import ConfigSourceProvider
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_di.definitions.enums.component_role_enum import ComponentRoleEnum
from framework.starter_web.context.access_log_record import AccessLogRecord
from framework.starter_web.context.error_log_record import ErrorLogRecord
from framework.starter_web.spi.access_log_provider import AccessLogProvider
from framework.starter_web.spi.error_log_provider import ErrorLogProvider
from module_infra.spi.config.config_support_provider_adapter import ConfigSupportProviderAdapter
from module_infra.spi.logger.api_access_log_service_provider_adapter import (
    ApiAccessLogServiceProviderAdapter,
)
from module_infra.spi.logger.api_error_log_service_provider_adapter import (
    ApiErrorLogServiceProviderAdapter,
)
from module_infra.spi.logger.dto.api_access_log_create_req_dto import ApiAccessLogCreateReqDTO
from module_infra.spi.logger.dto.api_error_log_create_req_dto import ApiErrorLogCreateReqDTO


@pytest.mark.parametrize(
    ("account_id", "user_id", "user_type"), [("17", 17, 2), (0, 0, 2), (None, None, 0)]
)
async def test_access_record_maps_to_infra_dto(account_id, user_id, user_type):
    began = datetime(2026, 10, 3, 9, 0)
    ended = began + timedelta(milliseconds=27)
    record = AccessLogRecord(
        trace_id="trace-17",
        account_id=account_id,
        tenant_id="tenant-5",
        method="POST",
        route="/items/{item_id}",
        client_ip="192.0.2.17",
        user_agent="safe-agent",
        operate_module="items",
        operate_name="create",
        operate_type=1,
        begin_time=began,
        end_time=ended,
        duration_ms=27,
        result_code=1234,
    )
    create_log = AsyncMock()
    adapter = ApiAccessLogServiceProviderAdapter()
    adapter.service = SimpleNamespace(create_api_access_log=create_log)
    adapter.settings = SimpleNamespace(application_id="configured-app")

    await adapter.write(record)

    create_log.assert_awaited_once()
    dto = create_log.await_args.args[0]
    assert isinstance(dto, ApiAccessLogCreateReqDTO)
    assert dto.model_dump(by_alias=False) == {
        "trace_id": "trace-17",
        "user_id": user_id,
        "user_type": user_type,
        "tenant_id": "tenant-5",
        "application_name": "configured-app",
        "request_method": "POST",
        "request_url": "/items/{item_id}",
        "request_params": None,
        "response_body": None,
        "user_ip": "192.0.2.17",
        "user_agent": "safe-agent",
        "operate_module": "items",
        "operate_name": "create",
        "operate_type": 1,
        "begin_time": began,
        "end_time": ended,
        "duration": 27,
        "result_code": 1234,
        "result_msg": "",
    }


@pytest.mark.parametrize(
    ("account_id", "user_id", "user_type"), [("17", 17, 2), (0, 0, 2), (None, None, 0)]
)
async def test_error_record_maps_to_infra_dto_and_uses_isolated_task(
    account_id, user_id, user_type
):
    """错误适配器直接映射框架事实，身份零值和匿名语义不依赖当前上下文。"""
    happened = datetime(2026, 10, 6, 9, 0)
    record = ErrorLogRecord(
        trace_id="trace-17",
        account_id=account_id,
        tenant_id="tenant-5",
        method="POST",
        route="/items/{item_id}",
        client_ip="192.0.2.17",
        user_agent="safe-agent",
        exception_time=happened,
        exception_name="ValueError",
        exception_message="错误提示",
        exception_stack_trace="安全堆栈",
        exception_class_name="builtins",
        exception_file_name="example.py",
        exception_method_name="execute",
        exception_line_number=17,
        result_code=500,
    )
    create_log = AsyncMock()

    async def run_isolated(writer, dto):
        """在替身执行域内调用业务写入方法。"""
        await writer(dto)

    adapter = ApiErrorLogServiceProviderAdapter()
    adapter.service = SimpleNamespace(create_api_error_log=create_log)
    adapter.settings = SimpleNamespace(application_id="configured-app")
    adapter.tasks = SimpleNamespace(run_isolated=AsyncMock(side_effect=run_isolated))

    await adapter.write(record)

    (dto,) = create_log.await_args.args
    assert isinstance(dto, ApiErrorLogCreateReqDTO)
    adapter.tasks.run_isolated.assert_awaited_once_with(create_log, dto)
    assert dto.model_dump(by_alias=False) == {
        "user_id": user_id,
        "user_type": user_type,
        "tenant_id": "tenant-5",
        "application_name": "configured-app",
        "request_method": "POST",
        "request_url": "/items/{item_id}",
        "request_params": {},
        "user_ip": "192.0.2.17",
        "user_agent": "safe-agent",
        "exception_time": happened,
        "exception_name": "ValueError",
        "exception_message": "错误提示",
        "exception_root_cause_message": "",
        "exception_stack_trace": "安全堆栈",
        "exception_class_name": "builtins",
        "exception_file_name": "example.py",
        "exception_method_name": "execute",
        "exception_line_number": 17,
        "trace_id": "trace-17",
    }


@pytest.mark.parametrize(
    ("adapter", "provider"),
    [
        (ApiAccessLogServiceProviderAdapter, AccessLogProvider),
        (ApiErrorLogServiceProviderAdapter, ErrorLogProvider),
        (ConfigSupportProviderAdapter, ConfigSourceProvider),
    ],
)
def test_infra_adapters_bind_framework_spi_as_services(adapter, provider):
    metadata = vars(adapter)[DiComponentMetadata.ATTRIBUTE]
    assert metadata.interface is provider
    assert metadata.role is ComponentRoleEnum.SERVICE
    assert provider in adapter.__bases__


async def test_config_refresh_preserves_workload_scope_and_update_result():
    calls = []
    result = ConfigUpdateResult(ConfigChange(2, ("web",)), ())
    get_config_map = AsyncMock(return_value={"web.enabled": True})

    @asynccontextmanager
    async def workload_scope(workload, tenant_id):
        calls.append(("enter", workload, tenant_id))
        yield
        calls.append(("exit", workload, tenant_id))

    async def refresh_external(loader):
        assert calls == [("enter", "infra.config.sync", "tenant-5")]
        assert loader is get_config_map
        return result

    adapter = ConfigSupportProviderAdapter()
    adapter.service = SimpleNamespace(get_config_map=get_config_map)
    adapter.configuration = SimpleNamespace(refresh_external=refresh_external)
    adapter.tenant = SimpleNamespace(default_tenant_id="tenant-5")
    adapter.workloads = SimpleNamespace(scope=workload_scope)

    assert await adapter.refresh() is result
    assert calls == [
        ("enter", "infra.config.sync", "tenant-5"),
        ("exit", "infra.config.sync", "tenant-5"),
    ]
