from typing import Protocol

from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.model.login_session import LoginSession
from framework.starter_web.routing.route_policy import RoutePolicy


class SecurityExecutionProvider(Protocol):
    """后台入口的可信执行契约；身份复验、租户和数据权限作用域由实现完整持有。"""

    @property
    def application_id(self) -> str: ...

    @property
    def context(self) -> SecurityContext: ...

    def validate_policy(self, policy: RoutePolicy) -> None: ...

    async def run_workload(
        self,
        source: str,
        callback,
        *args,
        capability: str,
        tenant_id: str | None = None,
        domain: str | None = None,
        **kwargs,
    ): ...

    async def issue_message(self, payload: bytes, *, audience: str) -> bytes: ...

    async def run_message(
        self,
        proof: bytes,
        payload: bytes,
        policy: RoutePolicy,
        callback,
        *args,
        audience: str,
        **kwargs,
    ): ...

    async def issue_workload_message(
        self, payload: bytes, *, audience: str, capability: str
    ) -> bytes: ...

    async def run_workload_message(
        self,
        proof: bytes,
        payload: bytes,
        callback,
        *args,
        audience: str,
        capability: str,
        domain: str | None = None,
        **kwargs,
    ): ...

    async def run_authenticated(self, resolver, policy: RoutePolicy, callback, *args, **kwargs): ...

    async def run_session_reference(
        self, expected: LoginSession, policy: RoutePolicy, callback, *args, **kwargs
    ): ...

    async def allowed_policies(self, policies): ...
