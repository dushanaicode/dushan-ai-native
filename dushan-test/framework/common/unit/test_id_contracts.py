import re

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from framework.common.contracts.snowflake_id import (
    SIGNED_BIGINT_MAX,
    SnowflakeCursorStr,
    SnowflakeIdInput,
    SnowflakeIdStr,
)
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.common.utils.id_utils import IdUtils

pytestmark = pytest.mark.unit


def test_random_identifiers_follow_explicit_contract():
    assert re.fullmatch(r"[a-zA-Z0-9]{21}", IdUtils.nano_id())
    assert re.fullmatch(r"[a-zA-Z0-9]{8}", IdUtils.nano_id(8))
    assert re.fullmatch(r"[a-f0-9]{32}", IdUtils.simple_uuid())
    with pytest.raises(ValueError):
        IdUtils.nano_id(0)


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


@pytest.mark.parametrize("ids", [["1"], ["1", str(SIGNED_BIGINT_MAX)]])
def test_id_list_request_parses_each_string_without_losing_precision(ids):
    request = IdListReqVO.model_validate({"ids": ids})
    assert request.ids == [int(value) for value in ids]


@pytest.mark.parametrize(
    "ids",
    [
        [],
        "1,2",
        "1",
        None,
        [1],
        [True],
        [1.0],
        [""],
        ["1,2"],
        ["0"],
        ["01"],
        ["-1"],
        ["+1"],
        ["1e3"],
        ["１２３"],
        [str(1 << 63)],
        ["1", "invalid"],
    ],
)
def test_id_list_request_rejects_invalid_wire_values(ids):
    with pytest.raises(ValidationError):
        IdListReqVO.model_validate({"ids": ids})


@pytest.mark.parametrize("payload", [{}, {"ids": ["1"], "extra": True}])
def test_id_list_request_rejects_missing_ids_and_unknown_fields(payload):
    with pytest.raises(ValidationError):
        IdListReqVO.model_validate(payload)
