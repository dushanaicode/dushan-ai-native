from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from framework.starter_security.public import SecurityErrorCodes, SecurityException
from module_system.service.workload.system_workload_service_impl import SystemWorkloadServiceImpl


class TestWorkloadTenantRequirement:
    async def test_global_workload_is_denied_with_per_tenant_guidance(self):
        """全局后台身份继续拒绝，并明确租户归属和逐租户执行方案。"""
        service = SystemWorkloadServiceImpl()
        service.settings = SimpleNamespace(workload_credential=SecretStr("x" * 32))
        service.security_settings = SimpleNamespace(application_id="test", domains=("admin",))

        with pytest.raises(SecurityException) as caught:
            await service.authenticate(
                "module_infra",
                application_id="test",
                domain="admin",
                capability="infra.job.log.clean",
                tenant_id=None,
            )

        assert caught.value.error_code is SecurityErrorCodes.DENIED
        assert "后台任务和消息必须属于某个租户" in caught.value.msg
        assert "不开放跨租户特权身份" in caught.value.msg
        assert "按租户逐个执行" in caught.value.msg
