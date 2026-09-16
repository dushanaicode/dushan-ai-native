from typing import Literal, Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity


class DataExemptionProvider(Protocol):
    """服务端核验资源、动作、租户和理由；不接受消息头声明的豁免。

    豁免只跳过记录范围，租户谓词、Security 和 Database 边界仍然生效。
    """

    async def authorize(
        self,
        identity: LoginSession | WorkloadIdentity,
        resource: str,
        operation: Literal["select", "insert", "update", "delete"],
        reason: str,
    ) -> bool: ...
