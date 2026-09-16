import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_ticket_origin_and_client_selector_rejections(socket_case):
    case = socket_case
    ticket = await case.ticket()
    url = case.url(ticket)
    attempts = [
        (url, {"origin": "https://wrong.example"}),
        (url, {}),
        (url + "&tenantId=2", {"origin": ORIGIN}),
        (url + "&access_token=must-not-log", {"origin": ORIGIN}),
        (url + "&ticket=duplicate", {"origin": ORIGIN}),
        (url, {"origin": ORIGIN, "additional_headers": {"Authorization": "Bearer must-not-log"}}),
        (url, {"origin": ORIGIN, "additional_headers": {"X-Tenant-ID": "2"}}),
        (url, {"origin": ORIGIN, "subprotocols": ["unknown"]}),
    ]
    for address, options in attempts:
        with pytest.raises(InvalidStatus) as rejected:
            async with connect(address, proxy=None, **options):
                pytest.fail("invalid handshake accepted")
        assert rejected.value.response.status_code == 403
    async with connect(url, origin=ORIGIN, proxy=None) as websocket:
        assert json.loads(await websocket.recv())["type"] == "connect"
    with pytest.raises(InvalidStatus):
        async with connect(url, origin=ORIGIN, proxy=None):
            pytest.fail("replayed ticket accepted")
    state = await case.wait_state(lambda value: value["runtime"]["connections"] == 0)
    assert state["connects"] == state["disconnects"] == 1
    log = (case.folder / "server.log").read_text(encoding="utf-8")
    assert ticket not in log and "must-not-log" not in log


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"subprotocols": ["dushan.v1"]}], indirect=True)
async def test_explicit_subprotocol_and_expired_ticket(socket_case):
    case = socket_case
    ticket = await case.ticket()
    async with connect(
        case.url(ticket), origin=ORIGIN, proxy=None, subprotocols=["dushan.v1"]
    ) as websocket:
        assert websocket.subprotocol == "dushan.v1"
        await websocket.recv()
    expired = await case.ticket()
    from framework.starter_security.core.opaque_token import OpaqueToken

    await case.redis.pexpire(case.prefix + ":ticket:" + OpaqueToken.digest(expired), 0)
    with pytest.raises(InvalidStatus):
        async with connect(
            case.url(expired), origin=ORIGIN, proxy=None, subprotocols=["dushan.v1"]
        ):
            pytest.fail("expired ticket accepted")


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize("ws_options", [{"max_connections_per_member": 1}], indirect=True)
async def test_connection_limit_releases_slot_and_old_cleanup_keeps_new_connection(socket_case):
    case = socket_case
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as first:
        previous = json.loads(await first.recv())["payload"]["clientId"]
        async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as rejected:
            with pytest.raises(ConnectionClosed) as closed:
                await rejected.recv()
            assert closed.value.rcvd.code == 4003
        assert (await case.state())["runtime"]["connections"] == 1
    await case.wait_state(lambda value: value["runtime"]["connections"] == 0)
    async with connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as current:
        replacement = json.loads(await current.recv())["payload"]["clientId"]
        assert replacement != previous
        await current.send('{"type":"ping"}')
        assert json.loads(await current.recv())["type"] == "pong"
        assert (await case.state())["runtime"]["connections"] == 1
