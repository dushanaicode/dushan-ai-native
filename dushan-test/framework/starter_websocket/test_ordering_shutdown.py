import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_default_order_preserved_while_ping_remains_responsive(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"wait","payload":{"text":"first"}}')
        await case.wait_state(lambda state: state["active"] == 1)
        await websocket.send('{"type":"echo","payload":{"text":"second"}}')
        await websocket.send('{"type":"ping"}')
        assert json.loads(await websocket.recv())["type"] == "pong"
        assert (await case.state())["received"] == ["first"]
        await case.http.post("/api/ws-test/release")
        assert [json.loads(await websocket.recv())["payload"]["text"] for _ in range(2)] == [
            "first",
            "second",
        ]


@pytest.mark.parametrize("ws_options", [{"handler_concurrency": 2}], indirect=True)
@pytest.mark.parametrize("ws_parallel", [True], indirect=True)
async def test_explicit_parallel_handlers_share_only_declared_limit(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"wait","payload":{"text":"first"}}')
        await case.wait_state(lambda state: state["active"] == 1)
        await websocket.send('{"type":"echo","payload":{"text":"second"}}')
        assert json.loads(await websocket.recv())["payload"]["text"] == "second"
        await case.http.post("/api/ws-test/release")
        assert json.loads(await websocket.recv())["payload"]["text"] == "first"


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_cancelled_close_waiter_keeps_real_cleanup(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await websocket.send('{"type":"wait","payload":{"text":"closing"}}')
        await case.wait_state(lambda state: state["active"] == 1)
        result = await case.http.post("/api/ws-test/cancel-close-waiter")
        assert result.json() == {"cancelled": True}
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(3):
                await websocket.recv()
        assert closed.value.rcvd.code == 1001
        state = await case.wait_state(lambda state: state["runtime"]["connections"] == 0)
        assert state["active"] == state["runtime"]["active_handlers"] == 0
