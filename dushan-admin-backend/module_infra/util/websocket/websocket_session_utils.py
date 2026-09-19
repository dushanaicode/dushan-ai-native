from framework.starter_di.public import (
    Inject,
    util,
)
from framework.starter_tenant.public import (
    TenantContext,
)
from framework.starter_websocket.public import (
    SocketTarget,
    SocketTargetKind,
)


@util
class WebSocketSessionUtils:
    tenant: TenantContext = Inject()

    def target(self, member_id=None, client_id=None):
        return SocketTarget(
            kind=SocketTargetKind.CLIENT
            if client_id
            else SocketTargetKind.MEMBER
            if member_id
            else SocketTargetKind.TENANT,
            audience="infra",
            tenant_id=self.tenant.get_required_tenant_id(),
            member_id=member_id,
            client_id=client_id,
        )
