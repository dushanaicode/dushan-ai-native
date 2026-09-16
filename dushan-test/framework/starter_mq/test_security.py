import asyncio
import base64
import hashlib
import hmac
import logging
import time

import pytest


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_tampered_signature_is_not_trusted(mq_case):
    case = mq_case
    message = await case.prepare(1)
    changed = message.envelope.model_copy(
        update={"payload": base64.b64encode(b'{"value":999}').decode()}
    )
    await case.runtime.backend.publish("events", message.mode, case.runtime.codec.encode(changed))
    await case.publish(2)
    await case.until(lambda: 2 in case.probe.finished)
    await asyncio.gather(*tuple(case.runtime.pending))
    assert [row[0] for row in case.probe.runs] == [2]
    assert case.runtime.rejected == 1


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize("attack", ["revoked", "expired", "tenant", "proof_body"])
async def test_current_authority_and_tenant_binding(mq_case, attack):
    case = mq_case
    message = await case.prepare(1)
    envelope = message.envelope
    if attack == "revoked":
        case.probe.revoked = True
    elif attack == "expired":
        now = time.time()
        envelope = envelope.model_copy(
            update={"issued_at": now - 120, "ready_at": now - 120, "expires_at": now - 60}
        )
    elif attack == "tenant":
        envelope = envelope.model_copy(update={"tenant_id": "1"})
    else:
        envelope = envelope.model_copy(
            update={"payload": base64.b64encode(b'{"value":999}').decode()}
        )
    body = case.runtime.codec.encode(case.runtime.codec.sign(envelope))
    await case.runtime.backend.publish("events", message.mode, body)
    await case.until(lambda: len(case.probe.records) == 1)
    assert not case.probe.runs
    assert case.probe.records[0].state.value == "rejected"


@pytest.mark.parametrize("mq_options", [{"external": True}], indirect=True)
@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
async def test_external_authentication_and_retry_reverify_security(mq_case):
    case = mq_case
    prepared = await case.prepare(1, behavior="retry")
    body = case.runtime.codec.encode(prepared.envelope)
    signature = hmac.new(case.module.External.SECRET, body, hashlib.sha256).hexdigest().encode()
    external = base64.b64encode(body) + b"." + signature
    await case.runtime.backend.publish("events", prepared.mode, external)
    await case.until(lambda: len(case.probe.records) == 2)
    assert [row[1] for row in case.probe.runs] == [0, 1]
    assert case.probe.finished == [1]


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
async def test_authority_dependency_failure_is_not_acknowledged_as_invalid(mq_case):
    case = mq_case
    prepared = await case.prepare(1)
    case.probe.auth_failure = True
    await case.service.send_prepared(prepared)
    await case.until(lambda: len(case.probe.records) == 1)
    case.probe.auth_failure = False
    await case.until(lambda: len(case.probe.records) == 2)
    assert len(case.probe.runs) == 1
    assert case.probe.runs[0][1] == 1
    assert case.runtime.rejected == 0


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
async def test_logs_do_not_expose_payload_or_proof(mq_case, caplog, capsys):
    case = mq_case
    caplog.set_level(logging.DEBUG)
    prepared = await case.prepare(1, behavior="fail")
    await case.service.send_prepared(prepared)
    await case.until(lambda: len(case.probe.records) == 3)
    text = caplog.text + capsys.readouterr().out
    assert "sensitive-mq-payload" not in text
    assert prepared.envelope.proof not in text
    assert prepared.envelope.payload not in text
    assert prepared.envelope.signature not in text
