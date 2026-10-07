from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml

from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.core.outbox_service import OutboxService
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.jobs.outbox_job import OutboxJob
from framework.starter_mq.model.outbox_job_parameters import OutboxJobParameters


@pytest.mark.parametrize(
    ("mq_enabled", "expected_error"),
    [(False, MQErrorCodes.CLOSED), (True, MQErrorCodes.CONFIGURATION)],
)
async def test_default_outbox_settings_require_disabled_job(mq_enabled, expected_error):
    backend = Path(__file__).resolve().parents[3] / "dushan-admin-backend"
    settings = yaml.safe_load((backend / "application.yaml").read_text(encoding="utf-8"))["config"][
        "models"
    ]["mq"]
    assert settings["enabled"] is False
    assert settings["outbox_enabled"] is False
    settings["enabled"] = mq_enabled
    mq = MQService()
    if settings["enabled"]:
        mq.runtime = SimpleNamespace(
            phase="ready", settings=SimpleNamespace(**settings), outbox=None, database=None
        )

    with pytest.raises(MQException) as caught:
        await OutboxJob(OutboxService(mq)).execute(OutboxJobParameters(), None)

    assert caught.value.error_code is expected_error


async def test_outbox_job_default_parameters_use_configured_batch_and_cleanup():
    outbox = SimpleNamespace(
        dispatch=AsyncMock(return_value={"published": 1}), cleanup=AsyncMock(return_value=2)
    )

    result = await OutboxJob(outbox).execute(OutboxJobParameters(), None)

    outbox.dispatch.assert_awaited_once_with(limit=None)
    outbox.cleanup.assert_awaited_once_with()
    assert result == {"published": 1, "cleaned": 2}
