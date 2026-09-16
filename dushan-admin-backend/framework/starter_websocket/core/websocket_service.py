import time
from uuid import uuid4

from framework.starter_di.decorators.components import framework
from framework.starter_websocket.enums.socket_target_kind import SocketTargetKind
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.model.socket_delivery import SocketDelivery
from framework.starter_websocket.model.socket_message import SocketMessage
from framework.starter_websocket.model.socket_receipt import SocketReceipt


@framework
class WebSocketService:
    """业务仅依赖发送/在线/失效端口，不访问本地连接字典。"""

    def __init__(self):
        self.runtime = None

    def require_runtime(self):
        if self.runtime is None or not self.runtime.accepting:
            raise SocketException("closed")
        return self.runtime

    async def _authorize(self, target):
        runtime = self.require_runtime()
        audience = runtime.registry.audience(target.audience)
        identity = runtime.security.context.current()
        workload = runtime.security.context.current_workload()
        if identity is not None:
            if "send" not in await runtime.security.allowed_policies(
                {"send": audience.send_policy}
            ):
                raise SocketException("policy")
            if target.kind is SocketTargetKind.AUDIENCE or target.tenant_id != identity.tenant_id:
                raise SocketException("policy")
        elif workload is not None:
            if (
                audience.workload_capability is None
                or audience.workload_capability not in workload.capabilities
            ):
                raise SocketException("policy")
            if workload.tenant_id is None:
                if not audience.allow_global_targets:
                    raise SocketException("policy")
            elif target.kind is SocketTargetKind.AUDIENCE or target.tenant_id != workload.tenant_id:
                raise SocketException("policy")
        else:
            raise SocketException("policy")
        return runtime, identity

    async def send(self, target, message):
        runtime, identity = await self._authorize(target)
        value = runtime.registry.event_payload(target.audience, message.type, message.payload)
        sender = None if identity is None else identity.membership_id
        if message.sender_id is not None and message.sender_id != sender:
            raise SocketException("policy")
        message = SocketMessage.model_validate_json(
            runtime.codec.encode(
                message.model_copy(
                    update={"payload": value.model_dump(mode="json"), "sender_id": sender}
                )
            ),
            by_name=False,
        )
        envelope = SocketDelivery(
            version=1,
            id=uuid4().hex,
            instance=runtime.instance,
            action="deliver",
            target=target,
            message=message,
            family_id=None,
            tenant_id=None,
            issued_at=time.time(),
            signature="0" * 64,
        )
        if runtime.transport is None:
            return SocketReceipt("local", runtime.receive_delivery(envelope))
        return SocketReceipt("redis", await runtime.transport.publish(envelope))

    async def online(self, target):
        runtime, _ = await self._authorize(target)
        if runtime.online is None:
            return tuple(
                connection.information
                for connection in runtime.connections.values()
                if connection.phase == "active" and runtime.matches(connection.information, target)
            )
        return await runtime.call(runtime.online.query(target))

    async def invalidate(self, *, family_id=None, tenant_id=None):
        runtime = self.require_runtime()
        if (family_id is None) == (tenant_id is None):
            raise SocketException("policy")
        identity = runtime.security.context.current()
        workload = runtime.security.context.current_workload()
        if workload is not None and "websocket:invalidate" in workload.capabilities:
            if workload.tenant_id is not None and tenant_id != workload.tenant_id:
                raise SocketException("policy")
        elif identity is None or tenant_id is not None or family_id != identity.family_id:
            raise SocketException("policy")
        envelope = SocketDelivery(
            version=1,
            id=uuid4().hex,
            instance=runtime.instance,
            action="invalidate",
            target=None,
            message=None,
            family_id=family_id,
            tenant_id=tenant_id,
            issued_at=time.time(),
            signature="0" * 64,
        )
        if runtime.transport is None:
            return SocketReceipt("local", runtime.receive_delivery(envelope))
        return SocketReceipt("redis", await runtime.transport.publish(envelope))
