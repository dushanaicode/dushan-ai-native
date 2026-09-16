import asyncio
import json
import os
import statistics
import time
from pathlib import Path

import pytest


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize(
    "mq_options",
    [
        {
            "settings": {
                "concurrency": 4,
                "prefetch": 8,
                "stream_max_length": 512,
                "kafka_partitions": 4,
            }
        }
    ],
    indirect=True,
)
async def test_representative_bounded_load(mq_case, tmp_path):
    case = mq_case
    count = 80
    payload = "x" * 1024
    submitted = {}

    async def send(index):
        submitted[index] = time.monotonic()
        return await case.publish(index, secret=payload)

    started = time.monotonic()
    await asyncio.gather(*(send(index) for index in range(count)))
    await case.until(lambda: len(case.probe.records) == count, seconds=30)
    elapsed = time.monotonic() - started
    delay = [
        case.probe.times[index] - submitted[row[0]] for index, row in enumerate(case.probe.runs)
    ]
    await case.runtime.close()
    resources = case.runtime.resources()
    assert sorted(case.probe.finished) == list(range(count))
    assert resources["peak_inflight"] <= 8
    assert resources["inflight"] == resources["active_consumers"] == resources["cancelling"] == 0
    report = {
        "backend": case.module.definition.mode.value,
        "messages": count,
        "payload_bytes": len(
            case.module.Payload(value=0, secret=payload).model_dump_json().encode()
        ),
        "concurrency": 4,
        "prefetch": 8,
        "kafka_partitions": 4,
        "elapsed_seconds": elapsed,
        "messages_per_second": count / elapsed,
        "dispatch_latency_p50_ms": statistics.median(delay) * 1000,
        "dispatch_latency_p95_ms": sorted(delay)[int(len(delay) * 0.95) - 1] * 1000,
        "resources_after_close": resources,
        "scope": "本机真实 broker、HMAC/当前身份验证、Redis claim、DI；不外推生产容量",
    }
    folder = Path(os.environ.get("DUSHAN_DP_REPORT_DIR", str(tmp_path)))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"mq-{report['backend']}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
