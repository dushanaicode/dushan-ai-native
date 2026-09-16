from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_tenant.model.tenant_provisioning_request import TenantProvisioningRequest
from framework.starter_tenant.model.tenant_provisioning_result import TenantProvisioningResult


class TenantProvisioningProvider(Protocol):
    """System 的开户事务；首次登录尚无租户是有效状态。

    必须在调用方事务内原子建立租户、成员/初始权限及持久幂等回执；同一账号、
    idempotency_key、请求正文只能生成同一结果，正文冲突必须拒绝。不得提前提交。
    fixed_tenant_id 非空时只能开通该默认租户，不得接管已属于他人的默认租户。
    会话签发必须在提交后由 System 执行，不能把 ACCOUNT 会话改字段充当租户会话。
    """

    async def provision(
        self,
        identity: LoginSession,
        request: TenantProvisioningRequest,
        *,
        fixed_tenant_id: str | None,
    ) -> TenantProvisioningResult: ...
