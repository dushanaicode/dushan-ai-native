from contextlib import AbstractAsyncContextManager
from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_web.routing.route_policy import RoutePolicy


class TenantAccessProvider(Protocol):
    """Tenant 拥有准入和隔离；不能用请求头切换已验证主体的 tenant_id。

    enter 必须重验成员/托管关系、租户状态、支持会话审批及路由资源限制，
    在完整执行内安装自己的隔离上下文，并在异常或取消后恢复。
    exit 在同一 Context/DI 执行的受保护任务中完成；不能跨 yield 持有任务专属
    数据库会话或事务，查询与事务继续使用 Database 自己的执行接点。
    Security 不替它生成数据库过滤条件或给平台身份授予租户权限。
    """

    def supports(self, capability: str) -> bool:
        """从已装配的部署配置判断能力上限；同步、无 I/O，供路由发布前校验。"""
        ...

    def enter(
        self, session: LoginSession, policy: RoutePolicy
    ) -> AbstractAsyncContextManager[None]: ...

    def enter_workload(
        self, identity: WorkloadIdentity, capability: str
    ) -> AbstractAsyncContextManager[None]:
        """检查系统能力对目标租户的准入并安装隔离上下文，不伪造 Membership。"""
        ...
