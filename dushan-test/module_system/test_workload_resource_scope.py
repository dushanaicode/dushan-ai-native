import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from fixtures.config_factory import ConfigFactory
from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_access_provider_adapter import (
    DataAccessProviderAdapter,
)
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.workload_message import WorkloadMessage
from module_system.service.tenant.tenant_service_impl import TenantServiceImpl
from module_system.service.workload.system_workload_service_impl import SystemWorkloadServiceImpl
from module_system.spi.permission.system_data_exemption_provider import SystemDataExemptionProvider

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")


@pytest.fixture
async def workload_scope(monkeypatch):
    """组装真实授权与豁免链，只替换租户存储和 DI 执行载体。"""
    application = SimpleNamespace()
    outside = SimpleNamespace(application=application, active=True)
    execution = ContextVar("workload_test_execution", default=outside)
    monkeypatch.setattr(ApplicationContext, "current_execution", execution.get)

    async def run_isolated(callback):
        binding = SimpleNamespace(application=application, active=True)
        token = execution.set(binding)
        try:
            return await callback()
        finally:
            binding.active = False
            execution.reset(token)

    application.tasks = SimpleNamespace(run_isolated=run_isolated)
    context = SecurityContext(application)
    models = ConfigFactory.values()["config"]["models"]
    settings = SecuritySettings.model_validate(
        {**models["security"], "enabled": True, "permission_cache_enabled": False}
    )
    workloads = SystemWorkloadServiceImpl()
    workloads.settings = SimpleNamespace(workload_credential=SecretStr("x" * 32))
    workloads.security_settings = settings
    authenticate = AsyncMock(side_effect=workloads.authenticate)
    permissions = DataPermissionService(
        DataPermissionSettings.model_validate(
            {**models["data_permission"], "enabled": True, "cache_enabled": False}
        ),
        context,
        None,
        None,
    )
    permissions.exemptions = SystemDataExemptionProvider()
    tenant = ContextVar("workload_test_tenant", default=None)
    grants = []

    @asynccontextmanager
    async def enter_workload(identity, capability):
        grant = await TenantServiceImpl().authorize_workload(identity, capability)
        grants.append(grant)
        token = tenant.set(grant.tenant_id)
        try:
            yield
        finally:
            tenant.reset(token)

    security = SecurityService(settings, None, None, None, context)
    await security.open(
        workloads=SimpleNamespace(authenticate=authenticate),
        tenant=SimpleNamespace(enter_workload=enter_workload),
        data_access=DataAccessProviderAdapter(permissions),
    )
    monkeypatch.setattr(ApplicationContext, "lookup", lambda _: security)
    yield SimpleNamespace(
        security=security,
        context=context,
        permissions=permissions,
        workloads=workloads,
        authenticate=authenticate,
        tenant=tenant,
        grants=grants,
    )
    await security.close()
    await permissions.close()


@pytest.mark.parametrize("tenant_id", ["1", "2"])
@pytest.mark.parametrize("ending", ["success", "failure", "cancel"])
@pytest.mark.parametrize(
    ("capability", "resource"),
    [
        ("infra.log.access.clean", "infra_api_access_log"),
        ("infra.log.error.clean", "infra_api_error_log"),
    ],
)
async def test_first_workload_entry_grants_only_current_capability(
    workload_scope, tenant_id, ending, capability, resource
):
    """首次进入只豁免指定日志的读取和删除，异常与取消都释放上下文。"""
    case = workload_scope
    saved = []

    async def clean():
        assert case.tenant.get() == tenant_id
        identity = case.context.current_workload()
        assert identity.tenant_id == tenant_id
        assert "infra.log.write" in identity.capabilities
        assert case.permissions.is_exempt(resource, "select")
        assert case.permissions.is_exempt(resource, "delete")
        assert not case.permissions.is_exempt(resource, "insert")
        other = (
            "infra_api_error_log" if resource == "infra_api_access_log" else "infra_api_access_log"
        )
        assert not case.permissions.is_exempt(other, "delete")
        assert not case.permissions.is_exempt("system_users", "select")
        saved.extend(case.permissions._exemptions.get())
        assert len(saved) == 2
        if ending == "failure":
            raise RuntimeError("清理失败")
        if ending == "cancel":
            raise asyncio.CancelledError()
        return 7

    if ending == "success":
        assert (
            await case.security.run_workload(
                "module_infra", clean, capability=capability, tenant_id=tenant_id
            )
            == 7
        )
    else:
        with pytest.raises(RuntimeError if ending == "failure" else asyncio.CancelledError):
            await case.security.run_workload(
                "module_infra", clean, capability=capability, tenant_id=tenant_id
            )
    case.authenticate.assert_awaited_once()
    assert len(case.grants) == 1
    assert {(entry.resource, entry.actions) for entry in case.grants[0].resources} == {
        (resource, frozenset({"select", "delete"}))
    }
    assert all(not entry.active and not entry.frame.active for entry in saved)
    assert case.permissions._active == 0
    assert case.permissions._exemptions.get() == ()
    assert case.context.current_workload() is None
    assert case.tenant.get() is None
    with pytest.raises(DataPermissionException):
        case.permissions.current()


async def test_nested_system_scope_restores_parent_permissions(workload_scope):
    """显式业务作用域复用首次授权入口，退出后恢复父能力及豁免。"""
    case = workload_scope

    async def clean():
        parent = case.context.current_workload()
        frame = case.permissions.current()
        async with case.workloads.scope("infra.log.write", "2"):
            assert case.tenant.get() == "2"
            assert case.permissions.is_exempt("infra_api_access_log", "insert")
            assert not case.permissions.is_exempt("infra_api_access_log", "delete")
        assert case.context.current_workload() is parent
        assert case.permissions.current() is frame
        assert case.tenant.get() == "1"
        assert case.permissions.is_exempt("infra_api_access_log", "delete")
        assert not case.permissions.is_exempt("infra_api_access_log", "insert")

    await case.security.run_workload(
        "module_infra", clean, capability="infra.log.access.clean", tenant_id="1"
    )
    assert case.authenticate.await_count == 2


@pytest.mark.parametrize("provider_present", [False, True])
async def test_empty_or_missing_exemption_provider_keeps_no_data_access(
    workload_scope, provider_present
):
    """空能力或无豁免提供者不扩大记录范围。"""
    case = workload_scope
    if not provider_present:
        case.permissions.exemptions = None

    async def observe():
        assert not case.permissions.is_exempt("infra_api_access_log", "delete")
        assert case.permissions._exemptions.get() == ()

    await case.security.run_workload(
        "module_infra", observe, capability="infra.database.observe", tenant_id="1"
    )


async def test_exemption_rejection_unwinds_before_business(workload_scope):
    """部分豁免建立后再遭拒绝时释放已建豁免，业务不得运行。"""
    case = workload_scope
    case.permissions.exemptions.authorize = AsyncMock(side_effect=[True, False])
    business = AsyncMock()
    with pytest.raises(DataPermissionException):
        await case.security.run_workload(
            "module_infra", business, capability="infra.log.access.clean", tenant_id="1"
        )
    business.assert_not_awaited()
    assert case.permissions._exemptions.get() == ()
    assert case.permissions._active == 0
    assert case.context.current_workload() is None
    assert case.tenant.get() is None


@pytest.mark.parametrize("capability", ["unknown", "system.auth"])
async def test_invalid_source_capability_rejected_before_data_access(workload_scope, capability):
    """未经来源授权的能力不能进入租户和数据豁免。"""
    case = workload_scope
    with pytest.raises(SecurityException):
        await case.security.run_workload(
            "module_infra", AsyncMock(), capability=capability, tenant_id="1"
        )
    assert not case.grants
    assert case.permissions._active == 0


async def test_workload_message_uses_its_verified_single_capability(workload_scope):
    """消息验证后仍只按信封能力建立资源豁免，不扩展到同来源能力。"""
    case = workload_scope
    capability = "infra.log.access.clean"
    identity = await case.workloads.authenticate(
        "module_infra",
        application_id=case.security.settings.application_id,
        domain=case.security.settings.default_domain,
        capability=capability,
        tenant_id="1",
    )
    case.security._messages = SimpleNamespace(
        verify_workload=AsyncMock(
            return_value=WorkloadMessage(identity=identity, capability=capability)
        )
    )

    async def consume(payload):
        assert payload == b"body"
        assert case.context.current_workload().capabilities == frozenset({capability})
        assert case.permissions.is_exempt("infra_api_access_log", "delete")
        assert not case.permissions.is_exempt("infra_api_error_log", "delete")

    await case.security.run_workload_message(
        b"x" * 32, b"body", consume, audience="module_infra", capability=capability
    )
    assert case.permissions._exemptions.get() == ()
    assert case.tenant.get() is None
