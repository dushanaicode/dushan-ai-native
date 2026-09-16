import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_real_handshake_message_and_distinct_execution(socket_case):
    case = socket_case
    ticket = await case.ticket()
    async with connect(case.url(ticket), origin=ORIGIN, proxy=None) as websocket:
        opened = json.loads(await websocket.recv())
        assert opened["type"] == "connect" and len(opened["payload"]["clientId"]) == 32
        assert isinstance(opened["timestamp"], int)
        protocol_pong = await websocket.ping(b"transport-ping")
        await asyncio.wait_for(protocol_pong, 1)
        for index in range(2):
            await websocket.send(
                json.dumps(
                    {"type": "echo", "payload": {"text": str(index)}, "requestId": str(index)}
                )
            )
            message = json.loads(await websocket.recv())
            assert message["type"] == "echo" and message["payload"] == {"text": str(index)}
            assert message["requestId"] == str(index)
        await websocket.send('{"type":"ping"}')
        assert json.loads(await websocket.recv())["type"] == "pong"
        state = await case.state()
        assert state["instances"] == state["distinct_instances"] == 2
        assert state["active_contexts"] == 0
    state = await case.wait_state(lambda state: state["runtime"]["connections"] == 0)
    assert state["connects"] == state["disconnects"] == 1
    assert state["runtime"]["error_types"] == []
    assert ticket not in (case.folder / "server.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_strict_envelope_unknown_types_and_safe_errors(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        for raw in (
            "{bad",
            '{"type":"echo","request_id":"old"}',
            '{"type":"echo","payload":{"text":"secret","other":1}}',
            '{"type":"echo","requestId":1}',
            '{"type":"not-registered"}',
            '{"type":"Echo"}',
            '{"type":"ping","timestamp":NaN}',
            '{"type":"ping","payload":{"x":1e400}}',
            '{"type":"echo","payload":{"text":"secret"},"senderId":"forged"}',
        ):
            await websocket.send(raw)
            message = json.loads(await websocket.recv())
            assert message["type"] == "error", (raw, message)
            assert "code" in message["payload"]
            assert "secret" not in json.dumps(message) and "forged" not in json.dumps(message)
        await websocket.send(
            '{"type":"echo","payload":{"text":"valid"},"requestId":"after-errors"}'
        )
        assert json.loads(await websocket.recv())["requestId"] == "after-errors"


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"max_message_bytes": 512}], indirect=True)
async def test_size_and_binary_boundaries(socket_case):
    case = socket_case
    for body, code in (
        (json.dumps({"type": "echo", "payload": {"text": "x" * 600}}), 1009),
        (b"binary", 1003),
    ):
        async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
            await websocket.recv()
            await websocket.send(body)
            with pytest.raises(ConnectionClosed) as closed:
                while True:
                    await websocket.recv()
            assert closed.value.rcvd.code == code
