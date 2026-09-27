import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from server.routing.application_health import ApplicationHealth


async def health(case):
    async with AsyncClient(
        transport=ASGITransport(app=case.app), base_url="http://testserver"
    ) as client:
        return await client.get("/health")


async def test_subscription_recovers_health_before_next_delivery(mq_case):
    case = mq_case
    actor = case.runtime.actors["controlled"]
    assert (await health(case)).status_code == 200
    async with asyncio.timeout(3):
        while True:
            clients = await case.runtime.replay.client.client_list()
            readers = [client for client in clients if client["cmd"] == "xreadgroup"]
            if readers:
                assert len(readers) == 1
                await case.runtime.replay.client.client_kill_filter(_id=readers[0]["id"])
                break
            await asyncio.sleep(0.01)
    async with asyncio.timeout(3):
        while not case.runtime.reconnect_attempts.get("controlled"):
            await asyncio.sleep(0.01)
    assert (await health(case)).status_code == 503
    async with asyncio.timeout(5):
        while (await health(case)).status_code != 200:
            await asyncio.sleep(0.02)
    assert not case.probe.runs
    assert case.runtime.actors["controlled"] is actor and not actor.done()
    await case.publish(73)
    await case.until(lambda: case.probe.finished == [73])


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_backend_health_and_closed_transport(mq_case):
    assert await mq_case.runtime.check_health()
    await mq_case.publish(74)
    await mq_case.until(lambda: mq_case.probe.finished == [74])
    assert await mq_case.runtime.check_health()
    await mq_case.runtime.close()
    assert not await mq_case.runtime.check_health()
    assert (await health(mq_case)).status_code == 503


@pytest.mark.parametrize(
    "mq_options",
    [
        {
            "settings": {
                "overrides": {
                    "controlled": {"enabled": False, "concurrency": None, "prefetch": None}
                }
            }
        }
    ],
    indirect=True,
)
async def test_producer_only_still_checks_broker(mq_case, monkeypatch):
    assert not mq_case.runtime.actors
    assert (await health(mq_case)).status_code == 200
    monkeypatch.setattr(ApplicationHealth, "PROBE_TIMEOUT_SECONDS", 0.15)
    client = mq_case.runtime.backend.client
    await client.client_pause(800, "ALL")
    response = await health(mq_case)
    assert response.status_code == 503
    assert response.json()["data"]["components"]["mq"] == "not_ready"
    await client.ping()
    assert (await health(mq_case)).status_code == 200


@pytest.mark.parametrize("mq_backend", ["rabbitmq"], indirect=True)
async def test_rabbit_publisher_loss_is_unhealthy_while_consumers_live(mq_case):
    assert (await health(mq_case)).status_code == 200
    await mq_case.runtime.backend.publisher.close()
    assert mq_case.runtime.phase == "ready"
    assert all(not task.done() for task in mq_case.runtime.actors.values())
    response = await health(mq_case)
    assert response.status_code == 503
    assert response.json()["data"]["components"]["mq"] == "not_ready"
