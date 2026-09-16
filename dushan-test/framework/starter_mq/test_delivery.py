import pytest


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_confirmed_delivery_and_context_cleanup(mq_case):
    case = mq_case
    receipt = await case.publish(1)
    await case.until(lambda: len(case.probe.records) == 1)
    assert case.probe.runs == [(1, 0, receipt.message_id, None)]
    assert case.probe.finished == [1]
    assert case.probe.records[0].state.value == "succeeded"
    assert case.probe.contexts == [("enter", receipt.message_id), ("exit", receipt.message_id)]
    with case.app.state.application_context.execution():
        assert case.app.state.security.context.current() is None
        assert case.app.state.security.context.current_workload() is None
    expected = {
        "stream": "stream_entry",
        "pubsub": "broadcast",
        "queue": "publisher_confirm",
        "topic": "partition_offset",
    }
    assert receipt.confirmation == expected[case.module.definition.mode.value]
