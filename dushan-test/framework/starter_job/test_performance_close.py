import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from statistics import median
from time import perf_counter

from sqlalchemy import select

from .test_runtime import wait_state


async def test_representative_load_and_closed_resources(job_case, job_target):
    case = job_case
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(parameters={"mode": "wait"}, max_instances=4))
        started = perf_counter()
        requests = [await case.service.trigger("job") for _ in range(12)]
    async with asyncio.timeout(5):
        while case.probe.active < 4:
            await asyncio.sleep(0.01)
    case.probe.release.set()
    for request in requests:
        await wait_state(case, request, "succeeded")
    elapsed = perf_counter() - started
    async with case.engine.connect() as connection:
        records = (await connection.scalars(select(case.module.RecordRow.spec))).all()
        messages = (await connection.scalars(select(case.module.RequestRow.spec))).all()
    submitted = {
        row["request_id"]: datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
        for row in messages
    }
    delays = sorted(
        (
            datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
            - submitted[row["request_id"]]
        ).total_seconds()
        * 1000
        for row in records
    )
    assert len(records) == 12 and case.probe.peak == 4
    await case.runtime.close()
    assert not case.runtime.running and not case.runtime.owner
    assert case.runtime.invoker.running_threads == 0
    result = {
        "database": job_target["name"],
        "requests": 12,
        "handler": "event-gated async",
        "concurrency": 4,
        "elapsed_seconds": elapsed,
        "requests_per_second": 12 / elapsed,
        "start_delay_p50_ms": median(delays),
        "start_delay_max_ms": max(delays),
        "resources_after": case.runtime.status(),
    }
    path = Path(os.environ["DUSHAN_DP_REPORT_DIR"])
    path.mkdir(parents=True, exist_ok=True)
    (path / f"job-{job_target['name']}.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
