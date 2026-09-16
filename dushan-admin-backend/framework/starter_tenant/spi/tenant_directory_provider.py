from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_tenant.model.tenant_access_grant import TenantAccessGrant
from framework.starter_tenant.model.tenant_info import TenantInfo
from framework.starter_web.routing.route_policy import RoutePolicy


class TenantDirectoryProvider(Protocol):
    """System 的租户目录和实时授权事实，不依赖当前租户来读取目录。

    查询必须使用权威主库。authorize_session 重验成员/托管关系、主体有效性、
    支持审批及资源限制；不能只相信 LoginSession 内的 ID 或客户端目标。
    租户创建、启停和删除须与部署控制记录采用同一事务并先锁定控制记录。
    租户标识永久不复用；删除目录记录不能使他人接管旧数据或已开通的默认租户。
    """

    async def get_tenant(self, tenant_id: str) -> TenantInfo | None: ...

    async def authorize_session(
        self, identity: LoginSession, policy: RoutePolicy
    ) -> TenantAccessGrant | None:
        """成员验证成功返回 None；支持会话必须返回获批资源到物理只读资源的映射。"""
        ...

    async def authorize_workload(
        self, identity: WorkloadIdentity, capability: str
    ) -> TenantAccessGrant: ...

    async def enabled_tenant_ids(self) -> tuple[str, ...]:
        """返回当前有效租户；空目录返回空 tuple，故障抛错。"""
        ...
