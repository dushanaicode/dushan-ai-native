from concurrent.futures import ThreadPoolExecutor

import pytest

from framework.starter_database.id.snowflake_utils import (
    MAX_SEQUENCE,
    SNOWFLAKE_EPOCH_MS,
    SnowflakeUtils,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", [True, -1, 1024, 1.5, "1"])
def test_snowflake_machine_number_is_explicit_and_strict(value):
    with pytest.raises(ValueError):
        SnowflakeUtils(value)


def test_snowflake_thread_safety_and_decoding():
    generator = SnowflakeUtils(23)
    with ThreadPoolExecutor(max_workers=4) as executor:
        values = list(executor.map(lambda _: generator.get_id(), range(100)))
    assert len(set(values)) == 100
    parsed = generator.parse_id(values[0])
    assert parsed["machine_id"] == 23
    assert parsed["datetime"].utcoffset().total_seconds() == 0
    assert generator.batch_ids(0) == []


def test_clock_rollback_exhaustion_and_epoch_overflow_fail_without_duplicate_ids(monkeypatch):
    generator = SnowflakeUtils(1)
    clock = [SNOWFLAKE_EPOCH_MS + 1000]
    monkeypatch.setattr(generator, "_current_timestamp_ms", lambda: clock[0])
    values = generator.batch_ids(MAX_SEQUENCE + 1)
    assert len(set(values)) == MAX_SEQUENCE + 1
    with pytest.raises(RuntimeError, match="用完"):
        generator.get_id()
    clock[0] -= 1
    with pytest.raises(RuntimeError, match="回退"):
        generator.get_id()
    clock[0] += 2
    assert generator.get_id() > values[-1]
    clock[0] = SNOWFLAKE_EPOCH_MS + (1 << 41)
    with pytest.raises(RuntimeError, match="纪元"):
        generator.get_id()
