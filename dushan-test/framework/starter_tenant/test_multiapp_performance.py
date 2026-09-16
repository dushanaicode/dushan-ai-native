import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import select

from framework.starter_tenant.exception.tenant_exception import TenantException
from server.starter_server import create_app


async def test_two_applications_do_not_share_tenant_context(tenant_case):
    case = tenant_case
    other = create_app(base_dir=case.config_path, environ={})
    async with other.router.lifespan_context(other):
        assert case.tenant.context is not other.state.tenant.context
        async with case.enter():
            with other.state.application_context.execution():
                with pytest.raises(TenantException):
                    case.tenant.context.current()
                with pytest.raises(TenantException):
                    other.state.tenant.context.current()
            assert case.tenant.context.get_required_tenant_id() == "1"
    async with case.enter():
        assert case.tenant.context.get_required_tenant_id() == "1"


async def test_representative_context_and_query_cost(tenant_case, tenant_target):
    case = tenant_case
    context_times = []
    query_times = []
    async with case.enter():
        for _ in range(100):
            started = perf_counter()
            assert case.tenant.context.get_required_tenant_id() == "1"
            context_times.append((perf_counter() - started) * 1000)
        async with case.database.read_session() as session:
            for _ in range(20):
                started = perf_counter()
                assert (
                    await session.scalars(
                        select(case.module.Record.id).order_by(case.module.Record.id)
                    )
                ).all() == [1, 2]
                query_times.append((perf_counter() - started) * 1000)
    result = {
        "database": tenant_target["name"],
        "context_median_ms": median(context_times),
        "query_median_ms": median(query_times),
        "context_samples": 100,
        "query_samples": 20,
        "active_after": case.tenant.context._active,
    }
    if "DUSHAN_DP_REPORT_DIR" in os.environ:
        directory = Path(os.environ["DUSHAN_DP_REPORT_DIR"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"tenant-{tenant_target['name']}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
