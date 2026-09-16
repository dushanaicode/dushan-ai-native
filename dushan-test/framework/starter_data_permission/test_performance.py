import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import select

from framework.starter_data_permission.enums.data_scope import DataScope


class Timings:
    def __init__(self):
        self.sql = []

    def observe(self, observation):
        self.sql.append(observation.elapsed_ms)


@pytest.mark.parametrize("permission_case", [{"cache": False}, {"cache": True}], indirect=True)
async def test_representative_cost_and_query_count(permission_case, permission_target):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY, DataScope.DEPT_AND_CHILD, DataScope.SELF)
    token, identity = case.issue()
    reads = []
    for _ in range(8):
        start = perf_counter()
        async with case.enter(token):
            assert case.service.require_membership_access("m3") == "t1"
        reads.append((perf_counter() - start) * 1000)
    assert case.provider.calls["memberships"] == (1 if case.service.settings.cache_enabled else 8)
    observer = Timings()
    conditions = []
    end_to_end = []
    async with case.enter(token):
        count = dict(case.provider.calls)
        for _ in range(100):
            start = perf_counter()
            case.policy.builder.condition(case.registry.require(case.Item.__table__), "select")
            conditions.append((perf_counter() - start) * 1000)
        with case.database.observe_queries(observer):
            async with case.database.read_session() as session:
                for _ in range(20):
                    start = perf_counter()
                    assert (
                        await session.scalars(select(case.Item.id).order_by(case.Item.id))
                    ).all() == [1, 2, 3, 4]
                    end_to_end.append((perf_counter() - start) * 1000)
        assert case.provider.calls == count
    assert len(observer.sql) == 20
    result = {
        "database": permission_target["name"],
        "cache": case.service.settings.cache_enabled,
        "permission_first_ms": reads[0],
        "permission_following_median_ms": median(reads[1:]),
        "condition_median_ms": median(conditions),
        "driver_sql_median_ms": median(observer.sql),
        "managed_select_median_ms": median(end_to_end),
        "sql_calls": 20,
        "scope_queries": dict(case.provider.calls),
        "samples": {"permission": 8, "condition": 100, "sql": 20},
    }
    if "DUSHAN_DP_REPORT_DIR" in os.environ:
        path = Path(os.environ["DUSHAN_DP_REPORT_DIR"])
        path.mkdir(exist_ok=True, parents=True)
        (path / f"{result['database']}-cache-{result['cache']}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
    if case.service.settings.cache_enabled:
        with case.application.execution():
            await case.service.cache.delete(
                case.service.settings.cache_key(), case.service._identifier(identity)
            )
