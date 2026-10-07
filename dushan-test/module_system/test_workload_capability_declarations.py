from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from framework.starter_di.public import ApplicationContext
from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
    WorkloadIdentity,
)
from module_system.definitions.constants.workload_constants import WorkloadConstants
from module_system.service.tenant.tenant_service_impl import TenantServiceImpl
from module_system.service.workload.system_workload_service_impl import SystemWorkloadServiceImpl
from module_system.spi.permission.system_data_exemption_provider import SystemDataExemptionProvider

pytestmark = pytest.mark.unit


@pytest.fixture
def workload_service():
    """构造不连接外部资源的工作负载服务。"""
    service = SystemWorkloadServiceImpl()
    service.settings = SimpleNamespace(workload_credential=SecretStr("x" * 32))
    service.security_settings = SimpleNamespace(application_id="test", domains=("admin",))
    return service


@pytest.mark.parametrize("capability", ["system.mail.send", "system.sms.send"])
@pytest.mark.parametrize("source", ["module_system", "system.auth"])
async def test_send_capabilities_allow_both_declared_sources(workload_service, source, capability):
    """短信和邮件同时允许业务及认证来源，但不扩大其他能力。"""
    identity = await workload_service.authenticate(
        source, application_id="test", domain="admin", capability=capability, tenant_id="1"
    )
    assert identity.audience == source
    assert identity.tenant_id == "1"
    assert {"system.mail.send", "system.sms.send"} <= identity.capabilities
    assert ("system.auth" in identity.capabilities) == (source == "system.auth")
    assert "infra.file.read" not in identity.capabilities


@pytest.mark.parametrize(
    ("source", "capability"),
    [("module_infra", "system.sms.send"), ("unregistered", "system.mail.send")],
)
async def test_source_cannot_claim_undeclared_capability(workload_service, source, capability):
    """来源不能领取其他来源的能力。"""
    with pytest.raises(SecurityException) as caught:
        await workload_service.authenticate(
            source, application_id="test", domain="admin", capability=capability, tenant_id="1"
        )
    assert caught.value.error_code is SecurityErrorCodes.DENIED


@pytest.mark.parametrize("capability", ["system.mail.send", "system.sms.send"])
async def test_local_scope_keeps_module_system_as_default(
    workload_service, monkeypatch, capability
):
    """多来源能力的本地调用始终选择 module_system。"""
    calls = []

    @asynccontextmanager
    async def authorized_workload(source, **kwargs):
        calls.append((source, kwargs))
        yield

    monkeypatch.setattr(
        ApplicationContext,
        "lookup",
        lambda _: SimpleNamespace(authorized_workload=authorized_workload),
    )
    async with workload_service.scope(capability, "1"):
        pass
    assert calls == [("module_system", {"capability": capability, "tenant_id": "1"})]


async def test_single_declaration_reaches_auth_tenant_and_exemption(monkeypatch):
    """新增能力仅声明一次，来源、租户授权和数据豁免共用该资源合同。"""
    monkeypatch.setattr(
        WorkloadConstants,
        "CAPABILITIES",
        {
            "test.export": {
                "source": "module_system",
                "additional_sources": ("system.auth",),
                "resources": {"system_users": frozenset({"select"})},
            }
        },
    )
    service = SystemWorkloadServiceImpl()
    service.settings = SimpleNamespace(workload_credential=SecretStr("x" * 32))
    service.security_settings = SimpleNamespace(application_id="test", domains=("admin",))
    identity = await service.authenticate(
        "system.auth",
        application_id="test",
        domain="admin",
        capability="test.export",
        tenant_id="1",
    )
    grant = await TenantServiceImpl().authorize_workload(identity, "test.export")
    assert grant.source == "system.auth"
    assert grant.tenant_id == "1"
    assert {(entry.resource, entry.actions) for entry in grant.resources} == {
        ("system_users", frozenset({"select"}))
    }
    provider = SystemDataExemptionProvider()
    assert await provider.workload_resources(identity, "test.export") == {
        "system_users": frozenset({"select"})
    }
    assert await provider.authorize(identity, "system_users", "select", "test.export")
    assert not await provider.authorize(identity, "system_users", "delete", "test.export")
    assert not await provider.authorize(identity, "system_post", "select", "test.export")


@pytest.mark.parametrize(
    ("source", "additional_sources", "resources"),
    [
        ("", (), {}),
        ("module_system", ("",), {}),
        ("module_system", ("module_system",), {}),
        ("module_system", (), {"system_users": frozenset({"drop"})}),
        ("module_system", (), {"system_users": frozenset()}),
    ],
)
def test_invalid_declarations_fail_at_service_construction(
    monkeypatch, source, additional_sources, resources
):
    """无效来源或资源动作在服务构建时拒绝，不推迟到任务执行。"""
    monkeypatch.setattr(
        WorkloadConstants,
        "CAPABILITIES",
        {
            "test.invalid": {
                "source": source,
                "additional_sources": additional_sources,
                "resources": resources,
            }
        },
    )
    with pytest.raises(ValueError):
        SystemWorkloadServiceImpl()


@pytest.mark.parametrize(
    ("tenant_id", "capabilities", "reason"),
    [
        (None, frozenset({"system.auth"}), "system.auth"),
        ("1", frozenset(), "system.auth"),
        ("1", frozenset({"unknown"}), "unknown"),
    ],
)
async def test_resource_authorization_keeps_tenant_and_capability_boundaries(
    tenant_id, capabilities, reason
):
    """缺少租户、身份能力或已登记能力时不授予资源。"""
    identity = WorkloadIdentity(
        application_id="test",
        domain="admin",
        service_id="service",
        tenant_id=tenant_id,
        audience="system.auth",
        capabilities=capabilities,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    assert not await SystemDataExemptionProvider().authorize(
        identity, "system_users", "select", reason
    )
    with pytest.raises(SecurityException) as caught:
        await TenantServiceImpl().authorize_workload(identity, reason)
    assert caught.value.error_code is SecurityErrorCodes.DENIED

    assert await SystemDataExemptionProvider().workload_resources(identity, reason) == {}
