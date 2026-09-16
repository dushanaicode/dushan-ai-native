import asyncio

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"transport": "redis"}], indirect=True)
async def test_subscription_close_failure_still_closes_connections(socket_case):
    case = socket_case
    case.process.expected_close_failure = True
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        result = await case.http.post("/api/ws-test/fail-close")
        assert result.json() == {"error": "ExceptionGroup", "connections": 0}
        with pytest.raises(ConnectionClosed) as closed:
            async with asyncio.timeout(3):
                await websocket.recv()
        assert closed.value.rcvd.code == 1001
