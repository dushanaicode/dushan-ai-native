import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from framework.common.contracts.snowflake_id import (
    SIGNED_BIGINT_MAX,
    SnowflakeCursorStr,
    SnowflakeIdInput,
    SnowflakeIdStr,
)
from framework.common.utils.id.id_utils import IdUtils
from framework.common.utils.id.snowflake_utils import (
    MAX_SEQUENCE,
    SNOWFLAKE_EPOCH_MS,
    SnowflakeUtils,
)

pytestmark = pytest.mark.unit


def test_random_identifiers_follow_explicit_contract():
    assert re.fullmatch(r"[a-zA-Z0-9]{21}", IdUtils.nano_id())
    assert re.fullmatch(r"[a-zA-Z0-9]{8}", IdUtils.nano_id(8))
    assert re.fullmatch(r"[a-f0-9]{32}", IdUtils.simple_uuid())
    with pytest.raises(ValueError):
        IdUtils.nano_id(0)


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


@pytest.mark.parametrize(
    "value", [True, False, 0, -1, 1.0, "01", "+1", "1e3", "１２３", str(1 << 63)]
)
def test_id_output_rejects_noncanonical_values(value):
    with pytest.raises(ValidationError):
        TypeAdapter(SnowflakeIdStr).validate_python(value)


@pytest.mark.parametrize("value", [1, True, 1.0, "0", "01", str(1 << 63)])
def test_id_input_requires_canonical_decimal_string(value):
    with pytest.raises(ValidationError):
        TypeAdapter(SnowflakeIdInput).validate_python(value)


def test_ids_keep_all_digits_in_json_and_schema():
    class Payload(BaseModel):
        request_id: SnowflakeIdInput
        response_id: SnowflakeIdStr
        optional_id: SnowflakeIdInput | None

    model = Payload(
        request_id=str(SIGNED_BIGINT_MAX), response_id=SIGNED_BIGINT_MAX, optional_id=None
    )
    assert model.request_id == SIGNED_BIGINT_MAX
    assert model.model_dump()["response_id"] == str(SIGNED_BIGINT_MAX)
    assert Payload.model_json_schema()["properties"]["request_id"]["type"] == "string"
    assert TypeAdapter(SnowflakeCursorStr).validate_python(0) == "0"
    with pytest.raises(ValidationError):
        TypeAdapter(SnowflakeCursorStr).validate_python(False)
