from contextlib import AbstractAsyncContextManager
from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity


class DataAccessProvider(Protocol):
    """认证及 Tenant 准入之后进入，覆盖 HTTP、任务和消息的完整授权执行。

    不得接管身份或租户准入；退出须在原 Context 内恢复自己的快照。
    退出可异步清理，由Security保护至真实终态，不能吞业务异常；提供者自行限制清理I/O时长。
    """

    def enter(
        self, identity: LoginSession | WorkloadIdentity, *, capability: str | None = None
    ) -> AbstractAsyncContextManager[None]:
        """会话不带能力；工作负载传入本次已验证的单一执行能力。"""
        ...
