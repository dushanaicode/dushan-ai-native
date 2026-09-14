from typing import Protocol

from framework.starter_security.model.workload_identity import WorkloadIdentity


class WorkloadProvider(Protocol):
    """Job/后台调用的本站服务认证接点；凭据和已注册任务授权由业务提供者持有。

    source 是请求认证的任务来源，不是权限证明。authenticate 必须核验当前应用
    所拥有的服务凭据、任务登记、指定能力及目标租户授权，不能照抄调用参数生成身份。
    无租户调用必须返回 tenant_id=None，不能从父请求继承租户；audience 绑定 source。
    """

    async def authenticate(
        self,
        source: str,
        *,
        application_id: str,
        domain: str,
        capability: str,
        tenant_id: str | None,
    ) -> WorkloadIdentity: ...
