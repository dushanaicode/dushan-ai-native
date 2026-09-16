import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from starter_websocket.conftest import ORIGIN

FAST = {
    "max_connections": 16,
    "authorization_concurrency": 16,
    "authorization_timeout_seconds": 0.05,
    "authorization_refresh_seconds": 0.05,
    "heartbeat_interval_seconds": 0.3,
    "heartbeat_timeout_seconds": 0.8,
}


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [FAST], indirect=True)
async def test_long_handler_does_not_block_heartbeat(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"wait","payload":{"text":"long"},"requestId":"long"}')
        await case.wait_state(lambda state: state["active"] == 1)
        await websocket.send('{"type":"ping","requestId":"alive"}')
        async with asyncio.timeout(2):
            while True:
                message = json.loads(await websocket.recv())
                if message["type"] == "ping":
                    await websocket.send('{"type":"pong"}')
                else:
                    assert message["type"] == "pong" and message["requestId"] == "alive"
                    break
        assert (await case.state())["active"] == 1
        await case.http.post("/api/ws-test/release")
        while True:
            message = json.loads(await websocket.recv())
            if message["type"] == "ping":
                await websocket.send('{"type":"pong"}')
            else:
                assert message["payload"] == {"text": "long"}
                break


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [FAST], indirect=True)
async def test_heartbeat_revalidates_idle_session(socket_case):
    case = socket_case
    _, identity = await case.issue(scopes=frozenset({"read"}))
    async with connect(
        case.url(await case.ticket(identity)), origin=ORIGIN, proxy=None
    ) as websocket:
        await websocket.recv()
        await case.save(identity.model_copy(update={"authorization_revision": "2"}))
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(2):
                while True:
                    await websocket.recv()
        assert closed.value.rcvd.code == 4001


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"inbound_queue_size": 1}], indirect=True)
async def test_inbound_queue_is_bounded(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"wait","payload":{"text":"active"}}')
        await case.wait_state(lambda state: state["active"] == 1)
        for value in ("queued", "overflow"):
            await websocket.send(json.dumps({"type": "wait", "payload": {"text": value}}))
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(2):
                while True:
                    await websocket.recv()
        assert closed.value.rcvd.code == 1013
    state = await case.wait_state(lambda state: state["runtime"]["connections"] == 0)
    assert state["maximum"] == 1 and state["active"] == 0


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize(
    "ws_options", [{"outbound_queue_size": 1, "send_timeout_seconds": 2}], indirect=True
)
async def test_slow_connection_does_not_block_fanout(socket_case):
    case = socket_case
    async with (
        connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as fast,
        connect(
            case.url(await case.ticket()),
            origin=ORIGIN,
            proxy=None,
            additional_headers={"X-WS-Test-Stall": "yes"},
        ) as slow,
    ):
        await fast.recv()
        await slow.recv()
        for value in range(3):
            response = await case.http.post(
                "/api/ws-test/send",
                json={
                    "target": {"kind": "audience", "audience": "test"},
                    "message": {"type": "echo", "payload": {"text": str(value)}},
                },
            )
            assert response.status_code == 200
            async with asyncio.timeout(1):
                assert json.loads(await fast.recv())["payload"] == {"text": str(value)}
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(2):
                await slow.recv()
        assert closed.value.rcvd.code == 1013
        assert (await case.state())["runtime"]["slow_connections"] == 1


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"send_timeout_seconds": 0.1}], indirect=True)
async def test_real_send_timeout_closes_connection(socket_case):
    case = socket_case
    async with connect(
        case.url(await case.ticket()),
        origin=ORIGIN,
        proxy=None,
        additional_headers={"X-WS-Test-Stall": "yes"},
    ) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"echo","payload":{"text":"slow"}}')
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(2):
                await websocket.recv()
        assert closed.value.rcvd.code == 1013


@pytest.mark.parametrize(
    "ws_options", [{"max_pending_handshakes": 1, "handshake_timeout_seconds": 0.5}], indirect=True
)
async def test_pending_handshake_limit_and_deadline(socket_case):
    case = socket_case
    await case.http.post("/api/ws-test/hold-handshake")

    async def open_one():
        return await connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None)

    first = asyncio.create_task(open_one())
    await case.wait_state(lambda state: state["runtime"]["handshakes"] == 1)
    with pytest.raises(InvalidStatus):
        await open_one()
    with pytest.raises(InvalidStatus):
        await first
    await case.wait_state(lambda state: state["runtime"]["handshakes"] == 0)
