from __future__ import annotations

import hashlib
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timedelta, timezone

from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.workload_identity import WorkloadIdentity
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
            raise SecurityException("configuration")
        if (
            application_id != self.security_settings.application_id
            or domain not in self.security_settings.domains
        ):
            raise SecurityException("invalid")
        if (
            source not in WorkloadConstants.SOURCES
            or capability not in WorkloadConstants.SOURCES[source]
            or tenant_id is None
        ):
            raise SecurityException("denied")
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
