import json
import os
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter

import pytest


@pytest.mark.skipif(
    "DUSHAN_SECURITY_MEASUREMENT" not in os.environ, reason="代表性测量由独立验收命令显式开启"
)
async def test_measure_real_authentication_and_permission_queries(security_factory):
    results = []
    for cached in (False, True):
        async with security_factory(cache=cached) as case:
            credentials = [
                await case.issue(
                    account_id=f"account-{index}",
                    granted=("read", *(f"resource:{n}" for n in range(63))),
                )
                for index in range(8)
            ]
            for token, _ in credentials:
                assert (await case.get(token)).json()["account"]
            start_tokens = case.service.tokens.reads
            start_permissions = case.service.permissions.reads
            durations = []
            for index in range(80):
                started = perf_counter()
                response = await case.get(credentials[index % 8][0])
                durations.append((perf_counter() - started) * 1000)
                assert response.json()["account"] == f"account-{index % 8}"
            results.append(
                {
                    "cache": cached,
                    "requests": 80,
                    "identities": 8,
                    "permissions_per_identity": 64,
                    "median_ms": median(durations),
                    "p95_ms": quantiles(durations, n=20)[18],
                    "authoritative_session_reads": case.service.tokens.reads - start_tokens,
                    "permission_provider_reads": case.service.permissions.reads - start_permissions,
                }
            )
    path = Path(os.environ["DUSHAN_SECURITY_MEASUREMENT"]).resolve()
    assert path.is_relative_to(Path.cwd().resolve() / "Temp")
    path.write_text(
        json.dumps(
            {
                "transport": "full ASGI HTTP chain",
                "database": "real SQLite",
                "cache": "real Redis 7.0.15",
                "concurrency": 1,
                "workloads": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
