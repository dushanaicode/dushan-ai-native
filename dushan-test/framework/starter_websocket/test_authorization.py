import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_inbound_and_outbound_permissions_are_separate(socket_case):
    case = socket_case
    _, restricted = await case.issue(scopes=frozenset({"send"}))
    async with (
        connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as reader,
        connect(case.url(await case.ticket(restricted)), origin=ORIGIN, proxy=None) as denied,
    ):
        await reader.recv()
        await denied.recv()
        await denied.send('{"type":"echo","payload":{"text":"not-allowed"},"requestId":"denied"}')
        rejected = json.loads(await denied.recv())
        assert rejected["type"] == "error" and rejected["payload"]["code"] == 403
        result = await case.http.post(
            "/api/ws-test/send",
            json={
                "target": {"kind": "audience", "audience": "test"},
                "message": {"type": "echo", "payload": {"text": "private-to-readers"}},
            },
        )
        assert result.status_code == 200
        assert json.loads(await reader.recv())["payload"] == {"text": "private-to-readers"}
        await denied.send('{"type":"ping"}')
        assert json.loads(await denied.recv())["type"] == "pong"
        assert (await case.state())["received"] == []


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_revocation_on_inbound_and_active_invalidation(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        await case.save(case.identity.model_copy(update={"revoked": True}))
        await websocket.send('{"type":"echo","payload":{"text":"after-revoke"}}')
        with pytest.raises(ConnectionClosed) as closed:
            while True:
                await websocket.recv()
        assert closed.value.rcvd.code == 4001
    await case.save(case.identity)
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as websocket:
        await websocket.recv()
        response = await case.http.post(
            "/api/ws-test/invalidate", json={"family_id": case.identity.family_id}
        )
        assert response.status_code == 200
        with pytest.raises(ConnectionClosed) as closed:
            await websocket.recv()
        assert closed.value.rcvd.code == 4001
    assert (await case.state())["received"] == []
