import asyncio
import time
from collections import Counter
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.websockets import WebSocket, WebSocketState

from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_websocket.core.online_registry import OnlineRegistry
from framework.starter_websocket.core.redis_socket_transport import RedisSocketTransport
from framework.starter_websocket.core.socket_codec import SocketCodec
from framework.starter_websocket.core.socket_connection import SocketConnection
from framework.starter_websocket.core.websocket_runtime import WebSocketRuntime
from framework.starter_websocket.core.websocket_service import WebSocketService
from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.exception.websocket_exception import WebSocketException
from framework.starter_websocket.model.socket_message import SocketMessage

pytestmark = pytest.mark.unit


async def call(awaitable):
    return await awaitable


async def test_transport_reconnect_survives_cleanup_and_subscribe_failures():
    errors = []
    consumed = asyncio.Event()

    async def receive(**kwargs):
        consumed.set()
        await asyncio.Future()

    initial = SimpleNamespace(
        get_message=AsyncMock(side_effect=OSError("read")),
        aclose=AsyncMock(side_effect=OSError("cleanup")),
    )
    replacement = SimpleNamespace(
        subscribe=AsyncMock(),
        get_message=AsyncMock(return_value={"type": "subscribe"}),
        aclose=AsyncMock(),
    )
    runtime = SimpleNamespace(
        settings=SimpleNamespace(
            command_timeout_seconds=0.1, transport_poll_seconds=0.001, transport_restart_seconds=0
        ),
        call=call,
        record_error=errors.append,
    )
    client = SimpleNamespace(pubsub=Mock(side_effect=[OSError("subscribe"), replacement]))
    transport = RedisSocketTransport(runtime, client, "channel")
    transport.subscription, transport.running, transport.connected = initial, True, True

    async def messages(**kwargs):
        replacement.get_message = receive
        return {"type": "subscribe"}

    replacement.get_message = messages
    transport.task = asyncio.create_task(transport._run())
    try:
        await asyncio.wait_for(consumed.wait(), 1)
        assert transport.connected and transport.reconnects == 1
        assert [str(error) for error in errors] == ["read", "cleanup", "subscribe"]
    finally:
        await transport.close()
    assert not transport.connected and transport.subscription is None


async def test_registry_remove_failure_preserves_local_cleanup_and_notification():
    connection = SimpleNamespace(
        id="c",
        session=SimpleNamespace(tenant_id="t"),
        information=object(),
        peak_inbound=2,
        peak_outbound=3,
        close_code=1001,
    )
    errors = []
    runtime = SimpleNamespace(
        connections={"c": connection},
        member_counts=Counter({"m": 1}),
        tenant_counts=Counter({"t": 1}),
        _member_key=lambda item: "m",
        peak_inbound=0,
        peak_outbound=0,
        online=SimpleNamespace(remove=AsyncMock(side_effect=OSError())),
        notify=AsyncMock(),
        call=call,
        record_error=errors.append,
    )
    await WebSocketRuntime.remove(runtime, connection)
    assert not runtime.connections and not runtime.member_counts and not runtime.tenant_counts
    assert len(errors) == 1
    runtime.notify.assert_awaited_once_with("disconnected", connection.information, 1001)


async def test_broken_listener_audience_is_isolated():
    good = SimpleNamespace(audience="test", connected=AsyncMock())

    async def isolated(callback):
        return await callback()

    runtime = SimpleNamespace(
        listeners=(object(), good),
        listener_failures=0,
        record_error=Mock(),
        call=call,
        application=SimpleNamespace(tasks=SimpleNamespace(run_isolated=isolated)),
    )
    information = SimpleNamespace(audience="test")
    await WebSocketRuntime.notify(runtime, "connected", information)
    assert runtime.listener_failures == 1
    good.connected.assert_awaited_once_with(information)


@pytest.mark.parametrize("translation_fails", [False, True])
def test_unknown_error_uses_internal_code_and_translation_failure_keeps_safe_text(
    translation_fails,
):
    connection = SocketConnection.__new__(SocketConnection)
    translator = Mock()
    translator.translate_any_scope.return_value = "translated"
    if translation_fails:
        translator.translate_any_scope.side_effect = ValueError("private template")
    connection.runtime = SimpleNamespace(translator=translator, record_error=Mock())
    connection.language = "en-US"
    connection.enqueue = Mock()
    connection.error_message(RuntimeError("private exception"))
    message = connection.enqueue.call_args.args[0]
    assert message.payload["code"] == WebSocketErrorCodes.INTERNAL.code
    assert message.payload["message"] == (
        WebSocketErrorCodes.INTERNAL.description if translation_fails else "translated"
    )
    assert WebSocketException(WebSocketErrorCodes.INTERNAL).is_system_error


async def test_sender_outside_wire_contract_is_policy_error():
    service = WebSocketService()
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            event_payload=lambda *args: SimpleNamespace(model_dump=lambda **kw: {})
        ),
        codec=SocketCodec(SimpleNamespace(max_message_bytes=4096)),
    )
    service._authorize = AsyncMock(
        return_value=(runtime, SimpleNamespace(membership_id="invalid member"))
    )
    with pytest.raises(WebSocketException) as caught:
        await service.send(SimpleNamespace(audience="test"), SocketMessage(type="event"))
    assert caught.value.error_code is WebSocketErrorCodes.POLICY


async def test_error_close_flushes_queued_frame_within_send_budget():
    connection = SocketConnection.__new__(SocketConnection)
    connection.runtime = SimpleNamespace(
        settings=SimpleNamespace(send_timeout_seconds=0.2), remove=AsyncMock(), record_error=Mock()
    )
    connection.websocket = SimpleNamespace(
        client_state=WebSocketState.CONNECTED,
        application_state=WebSocketState.CONNECTED,
        close=AsyncMock(),
    )
    connection.reader, connection.processors, connection.close_code = None, [], 1013
    connection.inbound, connection.outbound, connection.closed = (
        asyncio.Queue(),
        asyncio.Queue(),
        asyncio.Event(),
    )
    connection.outbound.put_nowait("error")
    sent = []

    async def sender():
        sent.append(await connection.outbound.get())
        await asyncio.sleep(0)
        connection.outbound.task_done()
        await asyncio.Future()

    connection.sender = asyncio.create_task(sender())
    await connection._close()
    assert sent == ["error"] and connection.closed.is_set()
    connection.websocket.close.assert_awaited_once_with(1013)


@pytest.mark.parametrize(
    "error_code", [WebSocketErrorCodes.UNKNOWN_TYPE, WebSocketErrorCodes.INTERNAL]
)
async def test_client_rejection_does_not_create_server_error_log(error_code):
    connection = SocketConnection.__new__(SocketConnection)

    async def reject(*args):
        raise WebSocketException(error_code)

    connection.audience = "test"
    connection.session = object()
    connection.runtime = SimpleNamespace(
        settings=SimpleNamespace(handler_timeout_seconds=0.1),
        record_error=Mock(),
        registry=SimpleNamespace(
            handlers={}, audience=lambda name: SimpleNamespace(policy=object())
        ),
        security=SimpleNamespace(run_session_reference=reject),
    )
    connection.inbound, connection.active_handlers = asyncio.Queue(), 0
    connection.error_message = Mock()
    connection.inbound.put_nowait(SocketMessage(type="unknown"))
    task = asyncio.create_task(connection._process())
    try:
        await asyncio.wait_for(connection.inbound.join(), 1)
        assert connection.runtime.record_error.call_count == int(
            error_code is WebSocketErrorCodes.INTERNAL
        )
        assert connection.error_message.call_count == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_handshake_rejection_close_failure_is_recorded():
    async def send(message):
        raise OSError("disconnected before accept")

    websocket = WebSocket({"type": "websocket"}, AsyncMock(), send)
    runtime = WebSocketRuntime.__new__(WebSocketRuntime)
    runtime.settings = SimpleNamespace(command_timeout_seconds=0.1)
    runtime.record_error = Mock()
    await runtime._reject(websocket, 4001)
    assert runtime.record_error.call_count == 1


async def test_received_disconnect_does_not_echo_reserved_close_code():
    connection = SocketConnection.__new__(SocketConnection)
    websocket = WebSocket(
        {"type": "websocket"},
        AsyncMock(return_value={"type": "websocket.disconnect", "code": 1006}),
        AsyncMock(),
    )
    websocket.client_state = websocket.application_state = WebSocketState.CONNECTED
    event = await websocket.receive()
    connection.websocket = websocket
    connection.runtime = SimpleNamespace(remove=AsyncMock(), record_error=Mock())
    connection.reader, connection.sender, connection.processors = None, None, []
    connection.close_code = event["code"]
    connection.inbound, connection.outbound, connection.closed = (
        asyncio.Queue(),
        asyncio.Queue(),
        asyncio.Event(),
    )
    await connection._close()
    websocket._send.assert_not_awaited()


async def test_cancel_during_resubscribe_bounds_remaining_subscription_close():
    entered = asyncio.Event()

    async def subscribe(*args):
        entered.set()
        await asyncio.Future()

    async def blocked_close():
        await asyncio.Future()

    replacement = SimpleNamespace(subscribe=subscribe, aclose=AsyncMock(side_effect=blocked_close))
    runtime = SimpleNamespace(
        settings=SimpleNamespace(
            command_timeout_seconds=0.03, transport_poll_seconds=0.001, transport_restart_seconds=0
        ),
        record_error=Mock(),
    )
    runtime.call = lambda awaitable: WebSocketRuntime.call(runtime, awaitable)
    transport = RedisSocketTransport(runtime, SimpleNamespace(pubsub=lambda **kw: replacement), "c")
    transport.subscription = SimpleNamespace(
        get_message=AsyncMock(side_effect=OSError("read")), aclose=AsyncMock()
    )
    transport.running = transport.connected = True
    transport.task = asyncio.create_task(transport._run())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        with pytest.raises(ExceptionGroup) as caught:
            await asyncio.wait_for(transport.close(), 1)
        assert len(caught.value.exceptions) == 1
        assert isinstance(caught.value.exceptions[0], TimeoutError)
        assert transport.task.cancelled()
        assert not transport.connected and not transport.running
        assert transport.subscription is None
        replacement.aclose.assert_awaited_once()
    finally:
        transport.task.cancel()
        await asyncio.gather(transport.task, return_exceptions=True)


async def test_local_delivery_failure_does_not_restart_subscription():
    consumed = asyncio.Event()

    async def wait_message(**kwargs):
        consumed.set()
        await asyncio.Future()

    subscription = SimpleNamespace(aclose=AsyncMock())

    async def first_message(**kwargs):
        subscription.get_message = wait_message
        return {"data": "envelope"}

    subscription.get_message = first_message
    runtime = SimpleNamespace(
        settings=SimpleNamespace(transport_poll_seconds=0.001),
        call=call,
        codec=SimpleNamespace(decode_delivery=Mock(return_value=object())),
        receive_delivery=Mock(side_effect=ValueError("local delivery")),
        record_error=Mock(),
    )
    transport = RedisSocketTransport(runtime, Mock(), "c")
    transport.subscription, transport.running, transport.connected = subscription, True, True
    transport.task = asyncio.create_task(transport._run())
    try:
        await asyncio.wait_for(consumed.wait(), 1)
        assert transport.connected and transport.reconnects == 0
        assert runtime.record_error.call_count == 1
    finally:
        await transport.close()


@pytest.mark.parametrize("translation_fails", [False, True])
@pytest.mark.parametrize("code", [SecurityErrorCodes.DENIED, SecurityErrorCodes.REVOKED])
def test_security_error_preserves_code_without_exposing_detail(code, translation_fails):
    connection = SocketConnection.__new__(SocketConnection)
    translator = Mock()
    translator.translate_any_scope.return_value = "public translation"
    if translation_fails:
        translator.translate_any_scope.side_effect = ValueError("private translation failure")
    connection.runtime = SimpleNamespace(translator=translator, record_error=Mock())
    connection.language, connection.enqueue = "en-US", Mock()
    connection.error_message(SecurityException(code, detail="private permission state"), "r")
    message = connection.enqueue.call_args.args[0]
    assert message.request_id == "r"
    assert message.payload == {
        "code": code.code,
        "message": code.description if translation_fails else "public translation",
    }
    assert connection.runtime.record_error.call_count == int(translation_fails)


@pytest.mark.parametrize("format_failed", [False, True])
def test_websocket_explicit_text_and_format_failure_do_not_retranslate(format_failed):
    error = WebSocketException(
        WebSocketErrorCodes.POLICY,
        msg="public {}" if format_failed else "public {literal}",
        format_args=() if format_failed else None,
    )
    connection = SocketConnection.__new__(SocketConnection)
    connection.runtime = SimpleNamespace(translator=Mock(), record_error=Mock())
    connection.language, connection.enqueue = "en-US", Mock()
    connection.error_message(error)
    assert connection.enqueue.call_args.args[0].payload == {
        "code": WebSocketErrorCodes.POLICY.code,
        "message": WebSocketErrorCodes.POLICY.description if format_failed else "public {literal}",
    }
    connection.runtime.translator.translate_any_scope.assert_not_called()


@pytest.mark.parametrize("translation_fails", [False, True])
def test_websocket_explicit_translation_key_and_arguments(translation_fails):
    error = WebSocketException(
        WebSocketErrorCodes.POLICY,
        msg="public {}",
        message_key="test.rejection",
        format_args=("reason",),
    )
    connection = SocketConnection.__new__(SocketConnection)
    translator = Mock()
    translator.translate_any_scope.return_value = "translated reason"
    if translation_fails:
        translator.translate_any_scope.side_effect = ValueError("template failure")
    connection.runtime = SimpleNamespace(translator=translator, record_error=Mock())
    connection.language, connection.enqueue = "en-US", Mock()
    connection.error_message(error)
    translator.translate_any_scope.assert_called_once_with(
        "test.rejection", "en-US", default="public reason", args=["reason"]
    )
    assert connection.enqueue.call_args.args[0].payload == {
        "code": WebSocketErrorCodes.POLICY.code,
        "message": "public reason" if translation_fails else "translated reason",
    }


@pytest.mark.parametrize("code", [1009, 1013, 4001])
async def test_error_flush_timeout_still_closes_and_removes_connection(code):
    connection = SocketConnection.__new__(SocketConnection)
    connection.runtime = SimpleNamespace(
        settings=SimpleNamespace(send_timeout_seconds=0.03), remove=AsyncMock(), record_error=Mock()
    )
    connection.websocket = SimpleNamespace(
        client_state=WebSocketState.CONNECTED,
        application_state=WebSocketState.CONNECTED,
        close=AsyncMock(),
    )
    connection.reader, connection.processors, connection.close_code = None, [], code
    connection.inbound, connection.outbound, connection.closed = (
        asyncio.Queue(),
        asyncio.Queue(),
        asyncio.Event(),
    )
    connection.outbound.put_nowait("error")
    entered = asyncio.Event()

    async def sender():
        await connection.outbound.get()
        entered.set()
        try:
            await asyncio.Future()
        finally:
            connection.outbound.task_done()

    connection.sender = asyncio.create_task(sender())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(connection._close(), 1)
        assert connection.sender.cancelled() and connection.closed.is_set()
        await asyncio.wait_for(connection.outbound.join(), 1)
        connection.websocket.close.assert_awaited_once_with(code)
        connection.runtime.remove.assert_awaited_once_with(connection)
    finally:
        connection.sender.cancel()
        await asyncio.gather(connection.sender, return_exceptions=True)


@pytest.mark.parametrize("cleanup_failure", [None, OSError, asyncio.CancelledError])
async def test_renew_retries_failed_removal_and_keeps_live_connections(cleanup_failure):
    runtime = SimpleNamespace(
        instance="instance",
        connections={"live": object()},
        settings=SimpleNamespace(instance_lease_seconds=10),
    )
    client = SimpleNamespace(
        eval=AsyncMock(side_effect=OSError("remove")),
        hkeys=AsyncMock(return_value=["removed", "live"]),
    )
    registry = OnlineRegistry(runtime, client, "prefix")
    registry.deadline = time.monotonic() + 10
    with pytest.raises(OSError):
        await registry.remove(SimpleNamespace(client_id="removed"))
    if cleanup_failure is not None:
        client.hkeys.side_effect = cleanup_failure("cleanup")
        with pytest.raises(cleanup_failure):
            await registry.renew()
        client.hkeys.side_effect = None
    client.eval.side_effect, client.eval.return_value = None, 1
    await registry.renew()
    assert client.eval.call_args.args[9:] == ("removed",)
    calls = client.hkeys.await_count
    await registry.renew()
    assert client.hkeys.await_count == calls
    assert client.eval.call_args.args[9:] == ()


async def test_new_removal_failure_during_renew_is_not_forgotten():
    runtime = SimpleNamespace(
        instance="instance", connections={}, settings=SimpleNamespace(instance_lease_seconds=10)
    )
    client = SimpleNamespace(
        eval=AsyncMock(side_effect=[OSError("first"), OSError("second"), 1, 1])
    )
    registry = OnlineRegistry(runtime, client, "prefix")
    registry.deadline = time.monotonic() + 10
    with pytest.raises(OSError):
        await registry.remove(SimpleNamespace(client_id="first"))

    async def snapshot(key):
        with pytest.raises(OSError):
            await registry.remove(SimpleNamespace(client_id="second"))
        return ["first"]

    client.hkeys = AsyncMock(side_effect=snapshot)
    await registry.renew()
    assert client.eval.call_args.args[9:] == ("first",)
    client.hkeys.side_effect, client.hkeys.return_value = None, ["second"]
    await registry.renew()
    assert client.hkeys.await_count == 2
    assert client.eval.call_args.args[9:] == ("second",)
