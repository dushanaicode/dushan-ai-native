from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.core.online_registry import OnlineRegistry
from framework.starter_websocket.core.socket_codec import SocketCodec
from framework.starter_websocket.core.websocket_service import WebSocketService
from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.definitions.enums.socket_target_kind import SocketTargetKind
from framework.starter_websocket.exception.websocket_exception import WebSocketException
from framework.starter_websocket.model.audience_definition import AudienceDefinition
from framework.starter_websocket.model.online_connection import OnlineConnection
from framework.starter_websocket.model.socket_message import SocketMessage
from framework.starter_websocket.model.socket_target import SocketTarget

pytestmark = pytest.mark.unit

QUERY = "infra:websocket:query"
SEND = "infra:websocket:send"
CAPABILITY = "websocket:dispatch"


def make_service(
    *, permissions=(), identity=None, workload=None, capability=None, global_targets=False
):
    audience = AudienceDefinition(
        key="infra",
        policy=RoutePolicy(permissions=(QUERY,), tenant_required=True, realm=SecurityRealm.TENANT),
        send_policy=RoutePolicy(
            permissions=(SEND,), tenant_required=True, realm=SecurityRealm.TENANT
        ),
        workload_capability=capability,
        allow_global_targets=global_targets,
    )

    async def allowed_policies(policies):
        return frozenset(
            key for key, policy in policies.items() if set(policy.permissions).issubset(permissions)
        )

    service = WebSocketService()
    service.runtime = SimpleNamespace(
        accepting=True,
        instance="1" * 32,
        security=SimpleNamespace(
            context=SimpleNamespace(current=lambda: identity, current_workload=lambda: workload),
            allowed_policies=AsyncMock(side_effect=allowed_policies),
        ),
        registry=SimpleNamespace(
            audience=lambda key: audience,
            event_payload=Mock(return_value=SimpleNamespace(model_dump=lambda **kwargs: {})),
        ),
        codec=SocketCodec(SimpleNamespace(max_message_bytes=4096)),
        transport=None,
        receive_delivery=Mock(return_value=1),
        online=None,
        connections={},
        matches=OnlineRegistry.matches,
    )
    return service


async def invoke(service, operation, target):
    if operation == "online":
        return await service.online(target)
    return await service.send(target, SocketMessage(type="status"))


async def test_query_permission_lists_only_active_connections_in_current_tenant_and_cannot_send():
    identity = SimpleNamespace(tenant_id="1", membership_id="reader")
    service = make_service(permissions={QUERY}, identity=identity)
    connections = []
    for index, (tenant, phase) in enumerate((("1", "active"), ("2", "active"), ("1", "closing"))):
        info = OnlineConnection(
            client_id=f"{index:032x}",
            instance="1" * 32,
            audience="infra",
            tenant_id=tenant,
            member_id="reader",
        )
        connections.append(info)
        service.runtime.connections[info.client_id] = SimpleNamespace(information=info, phase=phase)
    target = SocketTarget(kind=SocketTargetKind.TENANT, audience="infra", tenant_id="1")

    assert await service.online(target) == (connections[0],)
    with pytest.raises(WebSocketException) as caught:
        await service.send(target, SocketMessage(type="status"))
    assert caught.value.error_code is WebSocketErrorCodes.POLICY
    service.runtime.receive_delivery.assert_not_called()


async def test_send_permission_does_not_grant_audience_access_policy():
    service = make_service(
        permissions={SEND}, identity=SimpleNamespace(tenant_id="1", membership_id="sender")
    )
    target = SocketTarget(kind=SocketTargetKind.TENANT, audience="infra", tenant_id="1")
    await service.send(target, SocketMessage(type="status"))
    service.runtime.receive_delivery.assert_called_once()
    with pytest.raises(WebSocketException) as caught:
        await service.online(target)
    assert caught.value.error_code is WebSocketErrorCodes.POLICY


@pytest.mark.parametrize("operation", ["online", "send"])
@pytest.mark.parametrize(
    "target",
    [
        SocketTarget(kind=SocketTargetKind.TENANT, audience="infra", tenant_id="2"),
        SocketTarget(
            kind=SocketTargetKind.CLIENT, audience="infra", tenant_id="2", client_id="2" * 32
        ),
        SocketTarget(kind=SocketTargetKind.AUDIENCE, audience="infra"),
    ],
)
async def test_identity_cannot_target_other_tenant_or_all_tenants(operation, target):
    service = make_service(
        permissions={QUERY, SEND}, identity=SimpleNamespace(tenant_id="1", membership_id="reader")
    )
    with pytest.raises(WebSocketException) as caught:
        await invoke(service, operation, target)
    assert caught.value.error_code is WebSocketErrorCodes.POLICY


@pytest.mark.parametrize("operation", ["online", "send"])
async def test_anonymous_identity_cannot_query_or_send(operation):
    service = make_service()
    target = SocketTarget(kind=SocketTargetKind.TENANT, audience="infra", tenant_id="1")
    with pytest.raises(WebSocketException) as caught:
        await invoke(service, operation, target)
    assert caught.value.error_code is WebSocketErrorCodes.POLICY


@pytest.mark.parametrize("operation", ["online", "send"])
@pytest.mark.parametrize(
    "capability,capabilities,tenant_id,target_tenant,global_targets,allowed",
    [
        (None, {CAPABILITY}, "1", "1", False, False),
        (CAPABILITY, set(), "1", "1", False, False),
        (CAPABILITY, {CAPABILITY}, "1", "1", False, True),
        (CAPABILITY, {CAPABILITY}, "1", "2", False, False),
        (CAPABILITY, {CAPABILITY}, "1", None, True, False),
        (CAPABILITY, {CAPABILITY}, None, None, False, False),
        (CAPABILITY, {CAPABILITY}, None, None, True, True),
    ],
)
async def test_workload_keeps_capability_and_tenant_restrictions(
    operation, capability, capabilities, tenant_id, target_tenant, global_targets, allowed
):
    service = make_service(
        workload=SimpleNamespace(tenant_id=tenant_id, capabilities=capabilities),
        capability=capability,
        global_targets=global_targets,
    )
    target = SocketTarget(
        kind=SocketTargetKind.AUDIENCE if target_tenant is None else SocketTargetKind.TENANT,
        audience="infra",
        tenant_id=target_tenant,
    )
    if allowed:
        await invoke(service, operation, target)
    else:
        with pytest.raises(WebSocketException) as caught:
            await invoke(service, operation, target)
        assert caught.value.error_code is WebSocketErrorCodes.POLICY
    service.runtime.security.allowed_policies.assert_not_awaited()
