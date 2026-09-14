from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage


class MessageSecurityProvider(Protocol):
    """MQ 的认证信封接点，消息头本身不构成凭据。

    issue/verify 由已认证传输或成熟签名实现保证原始 payload、安全头、有效期、消费目标及
    重放策略；verify 还必须重读当前会话/权限版本和相关实时授权关系。
    未认证的 account_id、tenant_id 或角色字段不得构造 LoginSession。
    """

    async def issue(self, session: LoginSession, payload: bytes, *, audience: str) -> bytes: ...

    async def verify(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ) -> LoginSession: ...

    async def issue_workload(
        self, identity: WorkloadIdentity, payload: bytes, *, audience: str, capability: str
    ) -> bytes:
        """只签发已认证来源的收窄权限，任务启动凭据由 Job/业务提供者管理。"""
        ...

    async def verify_workload(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ) -> WorkloadMessage:
        """验证来源/正文/目标/重放和实时授权，返回证明中签发的单个能力。"""
        ...
