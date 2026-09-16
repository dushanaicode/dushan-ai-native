import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic

from framework.starter_cache.spi.tenant_context_provider import TenantContextProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_frame import TenantFrame


@framework(scope=ComponentScopeEnum.SINGLETON)
class TenantContext(TenantContextProvider):
    """应用独占的有效租户执行；不靠 ContextVar 继承取得新的执行授权。"""

    def __init__(self, application: ApplicationContext):
        self.application = application
        self._frame = ContextVar(f"tenant_{id(self)}", default=None)
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False

    def current(self) -> TenantFrame:
        frame = self._frame.get()
        if frame is None or not frame.active or not frame.execution.active:
            raise TenantException("missing")
        execution = ApplicationContext.current_execution()
        if execution is not frame.execution or execution.application is not self.application:
            raise TenantException("missing")
        if monotonic() >= frame.expires_at:
            raise TenantException("expired")
        return frame

    def get_required_tenant_id(self) -> str:
        return self.current().tenant_id

    @contextmanager
    def _bind(self, tenant_id, identity, *, seconds, resources=None, available=True):
        if self._closed:
            raise TenantException("closed")
        execution = ApplicationContext.current_execution()
        if execution.application is not self.application:
            raise TenantException("missing")
        frame = TenantFrame(
            execution, tenant_id, identity, resources, monotonic() + seconds, available
        )
        self._active += 1
        self._idle.clear()
        token = self._frame.set(frame)
        try:
            yield frame
        finally:
            frame.active = False
            self._frame.reset(token)
            self._active -= 1
            if not self._active:
                self._idle.set()

    def authorize_resource(self, resource, action):
        frame = self.current()
        if frame.resources is not None and not any(
            rule.resource == resource and action in rule.actions for rule in frame.resources
        ):
            raise TenantException("denied")

    async def close(self):
        self._closed = True
        await self._idle.wait()
