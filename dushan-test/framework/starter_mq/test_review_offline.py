import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.definitions.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_mq.core.mq_runtime import MQRuntime
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.core.outbox_service import OutboxService
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.definitions.enums.mq_backend import MQBackend
from framework.starter_mq.definitions.enums.outbox_state import OutboxState
from framework.starter_mq.definitions.enums.tenant_policy import TenantPolicy
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.delivery import Delivery
from framework.starter_mq.starter.mq_starter import MQStarter
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider

from .test_declarations import definition, handler, settings


async def test_activation_timeout_leaves_unsent_outbox_pending():
    runtime = MQRuntime.__new__(MQRuntime)
    runtime.settings = SimpleNamespace(
        command_timeout_seconds=0.005,
        outbox_enabled=True,
        outbox_batch_size=1,
        outbox_lease_seconds=30,
        outbox_max_attempts=3,
        max_retry_delay_seconds=60,
        outbox_retry_seconds=1,
    )
    runtime.ready, runtime.phase = asyncio.Event(), "starting"
    runtime.log_guard = SimpleNamespace(quiet=nullcontext)
    record = SimpleNamespace(
        state=OutboxState.SENDING,
        claim_expires_at=datetime.now(UTC) + timedelta(seconds=30),
        attempts=1,
        message=object(),
    )
    runtime.outbox = SimpleNamespace(claim=AsyncMock(return_value=record), finish=AsyncMock())
    runtime.database = object()
    mq = MQService()
    mq.runtime = runtime
    counts = await OutboxService(mq).dispatch()
    assert counts["pending"] == 1 and counts["unknown"] == 0
    assert runtime.outbox.finish.call_args.kwargs["state"] is OutboxState.PENDING
    assert runtime.outbox.finish.call_args.kwargs["error_type"] == "MQException"


async def test_prepared_unsupported_mode_has_declaration_error():
    mq = MQService()
    envelope = SimpleNamespace(destination="events")
    mq.runtime = SimpleNamespace(
        phase="ready",
        wait_ready=AsyncMock(),
        settings=SimpleNamespace(backend=MQBackend.REDIS),
        codec=SimpleNamespace(encode=lambda value: b"message", decode=lambda *args: envelope),
    )
    with pytest.raises(MQException) as caught:
        await mq.send_prepared(SimpleNamespace(envelope=envelope, mode=MessageMode.QUEUE))
    assert caught.value.error_code is MQErrorCodes.DECLARATION


@pytest.mark.parametrize("scenario", ["authenticator", "tenant"])
async def test_missing_consumer_dependency_is_rejected_before_transport(scenario):
    class Authenticator:
        async def authenticate(self, body, *, destination):
            pass

    component = handler(
        definition(
            external_authenticator=Authenticator if scenario == "authenticator" else None,
            tenant_policy=TenantPolicy.GLOBAL
            if scenario == "authenticator"
            else TenantPolicy.REQUIRED,
        )
    )
    container = SimpleNamespace(
        get_binding_diagnostics=lambda: [
            SimpleNamespace(
                component=CandidateSelection.qualified_name(component),
                outcome=BindingOutcomeEnum.SELECTED,
            )
        ],
        get_optional=lambda key: object() if key is MessageSecurityProvider else None,
        get=Mock(side_effect=AssertionError("transport dependencies must not be acquired")),
    )
    starter = MQStarter(
        settings(enabled=True, signing_secret="test-only-signing-secret-0123456789"),
        SimpleNamespace(container=container),
        MQService(),
    )
    with pytest.raises(MQException) as caught:
        await starter.open(
            components=[component],
            cache=object(),
            security=object(),
            tenant=None,
            database=None,
            job=None,
        )
    assert caught.value.error_code is (
        MQErrorCodes.DECLARATION if scenario == "authenticator" else MQErrorCodes.CONFIGURATION
    )
    container.get.assert_not_called()
    assert starter.runtime is None


@pytest.mark.parametrize("path", ["cancel", "busy"])
async def test_cancel_after_runner_release_does_not_release_transport_twice(path):
    released = asyncio.Event()
    calls = []

    async def release():
        calls.append("release")
        if len(calls) > 1:
            raise RuntimeError("Rabbit message already processed")
        released.set()

    delivery = Delivery(b"message", False, AsyncMock(), release)

    async def run(*args):
        await delivery.release()
        if path == "cancel":
            raise asyncio.CancelledError()
        return "busy"

    runtime = SimpleNamespace(
        runner=SimpleNamespace(run=run),
        call=lambda action: action,
        settings=SimpleNamespace(poll_seconds=10),
    )
    component = SimpleNamespace(__mq_consumer__=SimpleNamespace(key="test"))
    task = asyncio.create_task(
        MQRuntime._process(runtime, component, delivery, asyncio.Semaphore(1))
    )
    await released.wait()
    if path == "busy":
        await asyncio.sleep(0)
        task.cancel()
    await asyncio.wait_for(task, 1)
    assert calls == ["release"]


async def test_acknowledged_delivery_is_not_released_during_cleanup():
    acknowledge, release = AsyncMock(), AsyncMock()
    delivery = Delivery(b"message", False, acknowledge, release)
    await delivery.acknowledge()
    await delivery.release()
    acknowledge.assert_awaited_once_with()
    release.assert_not_awaited()


async def test_failed_release_does_not_claim_successful_settlement():
    release = AsyncMock(side_effect=[OSError("unconfirmed"), None])
    delivery = Delivery(b"message", False, AsyncMock(), release)
    with pytest.raises(OSError):
        await delivery.release()
    await delivery.release()
    assert release.await_count == 2


@pytest.mark.parametrize("lease", [20, 25])
def test_enabled_outbox_requires_claim_through_finish_budget(lease):
    with pytest.raises(ValidationError, match="认领至结算"):
        settings(outbox_enabled=True, command_timeout_seconds=5, outbox_lease_seconds=lease)
    assert settings(outbox_enabled=True, command_timeout_seconds=5, outbox_lease_seconds=26)
