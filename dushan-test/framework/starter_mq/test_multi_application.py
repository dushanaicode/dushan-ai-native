import asyncio

import pytest

from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.publish_command import PublishCommand


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_multiple_applications_follow_backend_delivery_semantics(mq_case):
    case = mq_case
    peer = await case.peer()
    await asyncio.gather(*(case.publish(value) for value in range(8)))
    if case.module.definition.mode.value == "pubsub":
        await case.until(lambda: len(case.probe.records) == 8 and len(peer.probe.records) == 8)
        assert sorted(case.probe.finished) == sorted(peer.probe.finished) == list(range(8))
    else:
        await case.until(lambda: len(case.probe.records) + len(peer.probe.records) == 8)
        assert sorted(case.probe.finished + peer.probe.finished) == list(range(8))
    assert len({id(item) for item in case.probe.instances}) == len(case.probe.instances)
    assert len({id(item) for item in peer.probe.instances}) == len(peer.probe.instances)
    assert all(not frame.active for frame in case.probe.executions + peer.probe.executions)


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_closing_one_application_preserves_other_application(mq_case):
    case = mq_case
    peer = await case.peer(
        config={"models": {"mq": {"namespace": case.runtime.settings.namespace + "_peer"}}}
    )
    await case.runtime.close()
    await peer.publish(9)
    await peer.until(lambda: peer.probe.finished == [9])
    assert not case.probe.runs
    assert peer.runtime.phase == "ready"


@pytest.mark.parametrize("mq_options", [{"settings": {"stream_max_length": 1}}], indirect=True)
async def test_stream_capacity_preserves_pending_and_trims_only_acknowledged(mq_case):
    case = mq_case
    await case.publish(1, behavior="wait")
    await case.until(lambda: case.probe.active == 1)
    with pytest.raises(MQException) as error:
        await case.publish(2)
    assert error.value.reason == "capacity"
    assert (
        await case.runtime.backend.client.xpending(
            case.runtime.backend.stream("events"), "test-group"
        )
    )["pending"] == 1
    case.probe.gate.set()
    await case.until(lambda: len(case.probe.records) == 1)
    await case.publish(2)
    await case.until(lambda: len(case.probe.records) == 2)
    assert case.probe.finished == [1, 2]
    assert await case.runtime.backend.client.xlen(case.runtime.backend.stream("events")) == 1


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize("mq_options", [{"second_consumer": True}], indirect=True)
async def test_multiple_declared_consumers_receive_only_their_destination(mq_case):
    case = mq_case
    await case.publish(1)
    await case.app.state.security.run_workload(
        "mq-test",
        lambda: case.service.publish(
            PublishCommand(
                "other",
                case.module.definition.mode,
                case.module.Payload(value=2),
                capability="mq:test",
            )
        ),
        capability="mq:test",
    )
    await case.until(lambda: len(case.probe.records) == 2)
    assert sorted(record.context.consumer_key for record in case.probe.records) == [
        "controlled",
        "secondary",
    ]
    assert sorted(case.probe.finished) == [1, 2]
