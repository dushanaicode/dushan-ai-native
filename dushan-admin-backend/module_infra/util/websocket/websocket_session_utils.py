from framework.starter_di.decorators.components import util
from framework.starter_di.decorators.inject import Inject
from framework.starter_tenant.context.tenant_context import TenantContext
from framework.starter_websocket.enums.socket_target_kind import SocketTargetKind
from framework.starter_websocket.model.socket_target import SocketTarget


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
