from __future__ import annotations

import hashlib
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timedelta, timezone

from framework.starter_data_permission.public import (
    DataPermissionService,
)
from framework.starter_di.public import (
    Inject,
    get_bean,
    service,
)
from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
    SecurityService,
    SecuritySettings,
    WorkloadIdentity,
)
from module_system.config.system_settings import SystemSettings
from module_system.definitions.constants.workload_constants import WorkloadConstants
from module_system.service.auth.system_workload_service import SystemWorkloadService


@service(interface=SystemWorkloadService)
class SystemWorkloadServiceImpl(SystemWorkloadService):
    settings: SystemSettings = Inject()
    security_settings: SecuritySettings = Inject()

    async def authenticate(self, source, *, application_id, domain, capability, tenant_id):
        credential = self.settings.workload_credential
        if credential is None or len(credential.get_secret_value()) < 32:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if (
            application_id != self.security_settings.application_id
            or domain not in self.security_settings.domains
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        if source not in WorkloadConstants.SOURCES:
            raise SecurityException(SecurityErrorCodes.DENIED, detail=f"未登记的来源：{source}")
        if capability not in WorkloadConstants.SOURCES[source]:
            raise SecurityException(
                SecurityErrorCodes.DENIED, detail=f"来源 {source} 不支持该能力：{capability}"
            )
        if tenant_id is None:
            raise SecurityException(SecurityErrorCodes.DENIED, detail="缺少租户上下文")
        service_id = hashlib.sha256(credential.get_secret_value().encode()).hexdigest()
        return WorkloadIdentity(
            application_id=application_id,
            domain=domain,
            service_id=service_id,
            tenant_id=tenant_id,
            audience=source,
            capabilities=WorkloadConstants.SOURCES[source],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    @asynccontextmanager
    async def scope(self, capability: str, tenant_id: str):
        """仅在运行期绑定认证入口，避免服务认证 SPI 反向依赖 Security 初始化。"""
        security = get_bean(SecurityService)
        permissions = get_bean(DataPermissionService)
        async with security.authorized_workload(
            WorkloadConstants.SOURCE_BY_CAPABILITY[capability],
            capability=capability,
            tenant_id=tenant_id,
        ):
            async with AsyncExitStack() as stack:
                for resource, actions in WorkloadConstants.RESOURCES[capability].items():
                    if resource in WorkloadConstants.PROTECTED:
                        for action in actions:
                            await stack.enter_async_context(
                                permissions.exempt(resource, action, reason=capability)
                            )
                yield
