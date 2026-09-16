import asyncio
import json
import time
from uuid import uuid4

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
@pytest.mark.parametrize(
    "ws_options", [{"transport": "redis", "transport_restart_seconds": 0.05}], indirect=True
)
async def test_two_process_delivery_online_and_active_invalidation(socket_case):
    case = socket_case
    peer = await case.peer()
    one_state, two_state = await case.state(), await peer.state()
    assert one_state["pid"] != two_state["pid"]
    assert one_state["runtime"]["instance_id"] != two_state["runtime"]["instance_id"]
    async with (
        connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as one,
        connect(peer.url(await peer.ticket()), origin=ORIGIN, proxy=None) as two,
    ):
        first = json.loads(await one.recv())["payload"]["clientId"]
        second = json.loads(await two.recv())["payload"]["clientId"]
        online = await case.http.post(
            "/api/ws-test/online", json={"kind": "audience", "audience": "test"}
        )
        assert sorted(item["client_id"] for item in online.json()) == sorted([first, second])
        sent = await case.http.post(
            "/api/ws-test/send",
            json={
                "target": {"kind": "client", "audience": "test", "client_id": second},
                "message": {"type": "echo", "payload": {"text": "remote"}},
            },
        )
        assert sent.json()["transport"] == "redis" and sent.json()["accepted"] == 2
        assert json.loads(await two.recv())["payload"] == {"text": "remote"}
        await case.http.post(
            "/api/ws-test/send",
            json={
                "target": {"kind": "audience", "audience": "test"},
                "message": {"type": "echo", "payload": {"text": "all"}},
            },
        )
        assert json.loads(await one.recv())["payload"] == {"text": "all"}
        assert json.loads(await two.recv())["payload"] == {"text": "all"}
        await case.http.post("/api/ws-test/invalidate", json={"family_id": case.identity.family_id})
        for websocket in (one, two):
            with pytest.raises(ConnectionClosed) as closed:
                async with asyncio.timeout(3):
                    await websocket.recv()
            assert closed.value.rcvd.code == 4001
    await case.wait_state(lambda value: value["runtime"]["connections"] == 0)
    await peer.wait_state(lambda value: value["runtime"]["connections"] == 0)
    assert (
        await case.http.post("/api/ws-test/online", json={"kind": "audience", "audience": "test"})
    ).json() == []


@pytest.mark.parametrize(
    "ws_options", [{"transport": "redis", "transport_restart_seconds": 0.05}], indirect=True
)
async def test_tampered_envelope_and_subscription_recovery(socket_case):
    case = socket_case
    peer = await case.peer("granian")
    async with connect(peer.url(await peer.ticket()), origin=ORIGIN, proxy=None) as websocket:
        client_id = json.loads(await websocket.recv())["payload"]["clientId"]
        state = await peer.state()
        forged = {
            "version": 1,
            "id": uuid4().hex,
            "instance": uuid4().hex,
            "action": "deliver",
            "target": {"kind": "client", "audience": "test", "client_id": client_id},
            "message": {"type": "echo", "payload": {"text": "forged"}, "timestamp": 0},
            "family_id": None,
            "tenant_id": None,
            "issued_at": time.time(),
            "signature": "0" * 64,
        }
        await case.redis.publish(state["online_prefix"] + ":broadcast", json.dumps(forged))
        await peer.wait_state(lambda value: value["runtime"]["rejected_envelopes"] == 1)
        await peer.http.post("/api/ws-test/drop-subscription")
        await peer.wait_state(lambda value: value["runtime"]["subscription_reconnects"] >= 1)
        result = await case.http.post(
            "/api/ws-test/send",
            json={
                "target": {"kind": "client", "audience": "test", "client_id": client_id},
                "message": {"type": "echo", "payload": {"text": "after-recovery"}},
            },
        )
        assert result.status_code == 200
        assert json.loads(await websocket.recv())["payload"] == {"text": "after-recovery"}


@pytest.mark.parametrize("ws_options", [{"transport": "redis"}], indirect=True)
async def test_process_death_and_expired_instance_are_not_permanently_online(socket_case):
    case = socket_case
    peer = await case.peer()
    async with (
        connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None) as one,
        connect(peer.url(await peer.ticket()), origin=ORIGIN, proxy=None) as two,
    ):
        live = json.loads(await one.recv())["payload"]["clientId"]
        dead = json.loads(await two.recv())["payload"]["clientId"]
        before = await peer.state()
        await peer.crash()
        with pytest.raises(ConnectionClosed):
            await two.recv()
        prefix, instance = before["online_prefix"], before["runtime"]["instance_id"]
        # 真实 Redis 的到期边界直接推进，避免长 sleep。
        await case.redis.pexpire(prefix + ":instance:" + instance, 0)
        await case.redis.zadd(prefix + ":instances", {instance: time.time() - 1})
        result = await case.http.post(
            "/api/ws-test/online", json={"kind": "audience", "audience": "test"}
        )
        assert [item["client_id"] for item in result.json()] == [live]
        assert dead != live
