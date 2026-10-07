from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from framework.starter_di.public import (
    ApplicationContext,
    Inject,
    service,
)
from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
    SecurityService,
    SecuritySettings,
    WorkloadIdentity,
)
from framework.starter_tenant.public import TenantResourceGrant
from module_system.config.system_settings import SystemSettings
from module_system.definitions.constants.workload_constants import WorkloadConstants
from module_system.service.workload.system_workload_service import SystemWorkloadService


@service(interface=SystemWorkloadService)
class SystemWorkloadServiceImpl(SystemWorkloadService):
    settings: SystemSettings = Inject()
    security_settings: SecuritySettings = Inject()

    def __init__(self):
        """校验能力声明，并从本地来源及额外来源构建授权索引。"""
        sources: dict[str, set[str]] = {}
        for capability, definition in WorkloadConstants.CAPABILITIES.items():
            source = definition["source"]
            additional_sources = definition["additional_sources"]
            if not capability or not source or source in additional_sources:
                raise ValueError(f"工作负载能力来源声明无效：{capability}")
            for allowed_source in (source, *additional_sources):
                if not allowed_source:
                    raise ValueError(f"工作负载能力来源为空：{capability}")
                sources.setdefault(allowed_source, set()).add(capability)
            for resource, actions in definition["resources"].items():
                TenantResourceGrant(resource=resource, actions=actions)
        self._capabilities_by_source = {
            source: frozenset(capabilities) for source, capabilities in sources.items()
        }

    async def authenticate(self, source, *, application_id, domain, capability, tenant_id):
        """按服务端登记的来源、能力和租户认证后台身份。"""
        credential = self.settings.workload_credential
        if credential is None or len(credential.get_secret_value()) < 32:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if (
            application_id != self.security_settings.application_id
            or domain not in self.security_settings.domains
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        if source not in self._capabilities_by_source:
            raise SecurityException(SecurityErrorCodes.DENIED, detail=f"未登记的来源：{source}")
        if capability not in self._capabilities_by_source[source]:
            raise SecurityException(
                SecurityErrorCodes.DENIED, detail=f"来源 {source} 不支持该能力：{capability}"
            )
        if tenant_id is None:
            raise SecurityException(
                SecurityErrorCodes.DENIED,
                detail="后台任务和消息必须属于某个租户，不开放跨租户特权身份；覆盖全部租户请使用按租户逐个执行的任务",
            )
        service_id = hashlib.sha256(credential.get_secret_value().encode()).hexdigest()
        return WorkloadIdentity(
            application_id=application_id,
            domain=domain,
            service_id=service_id,
            tenant_id=tenant_id,
            audience=source,
            capabilities=self._capabilities_by_source[source],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    @asynccontextmanager
    async def scope(self, capability: str, tenant_id: str):
        """SecurityService 只在运行期查找：它的构造依赖 TokenProvider → OAuth2TokenServiceImpl →
        本服务，改为 Inject 会让 DI 启动时成环，因此要求 di.lookup_enabled 保持开启。
        """
        security = ApplicationContext.lookup(SecurityService)
        definition = WorkloadConstants.CAPABILITIES[capability]
        async with security.authorized_workload(
            definition["source"],
            capability=capability,
            tenant_id=tenant_id,
        ):
            yield
