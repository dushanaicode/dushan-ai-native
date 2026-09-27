import asyncio
from types import SimpleNamespace

import pytest

from framework.starter_protection.core.protection_service import ProtectionService
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.idempotent.idempotency_claim import IdempotencyClaim


@pytest.mark.parametrize(
    "code, retryable", [(Codes.INVALID, False), (Codes.CLOSED, True), (Codes.UNAVAILABLE, True)]
)
def test_only_deterministic_invalid_protection_input_is_not_retryable(code, retryable):
    assert ProtectionException(code).retryable is retryable


async def test_close_during_open_probe_cannot_resurrect_service(settings):
    entered, release = asyncio.Event(), asyncio.Event()

    async def probe(*args):
        entered.set()
        await release.wait()
        return 1

    service = ProtectionService(settings(), SimpleNamespace(eval_atomic=probe))
    opening = asyncio.create_task(service.open())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        await service.close()
        release.set()
        with pytest.raises(ProtectionException) as caught:
            await opening
        assert caught.value.error_code is Codes.CLOSED
        assert service.resources()["state"] == "closed" and service.runtime.observer is None
    finally:
        release.set()
        await asyncio.gather(opening, return_exceptions=True)
        await service.close()


async def test_disabled_lock_and_unknown_idempotency_outcome_are_observed(settings, subject):
    events = []
    service = ProtectionService(settings(enabled=False), None)

    def observer(event):
        assert service.runtime.active == 1
        events.append(event)

    await service.open(observer=observer)
    try:
        with pytest.raises(ProtectionException) as caught:
            await service.locks.acquire("review", subject)
        assert caught.value.error_code is Codes.INVALID and not caught.value.retryable
        claim = IdempotencyClaim("key", "owner", service.settings.idempotency)
        assert await service.idempotency.fail(claim, known_no_effect=False) == "retained"
        assert [(event.feature, event.action, event.outcome) for event in events] == [
            ("lock", "acquire", "disabled"),
            ("idempotency", "fail", "retained"),
        ]
    finally:
        await service.close()
