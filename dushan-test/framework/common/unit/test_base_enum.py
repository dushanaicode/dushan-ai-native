from enum import IntEnum, StrEnum
from typing import Annotated

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, BeforeValidator, TypeAdapter, ValidationError

from framework.common.enums.base_enum import BaseEnum
from framework.common.enums.status_enum import StatusEnum


class ChannelEnum(BaseEnum):
    """字符串编码示例。"""

    WEB = ("web", "网页")
    APP = ("app", "应用")


class ForeignIntEnum(IntEnum):
    """另一种整数枚举，用来检查是否会误收其他枚举的成员。"""

    VALUE = 1


class ForeignStrEnum(StrEnum):
    """另一种字符串枚举，用来检查值相同时会不会被误收。"""

    VALUE = "web"


StrictStatus = Annotated[StatusEnum, BeforeValidator(StatusEnum.from_code)]
StrictChannel = Annotated[ChannelEnum, BeforeValidator(ChannelEnum.from_code)]


class Payload(BaseModel):
    """用于枚举接口测试的请求和响应模型。"""

    status: StrictStatus
    channel: StrictChannel


def test_identity_lookup_and_display_remain_separate():
    assert StatusEnum.from_code(0) is StatusEnum.DISABLE
    assert StatusEnum.from_code(StatusEnum.DISABLE) is StatusEnum.DISABLE
    assert StatusEnum["DISABLE"] is StatusEnum.DISABLE
    assert StatusEnum.DISABLE.code == StatusEnum.DISABLE.value == 0
    assert StatusEnum.DISABLE.label == "关闭"
    assert str(StatusEnum.DISABLE) == "0"
    assert StatusEnum.DISABLE != 0
    assert StatusEnum.get_by_label("关闭") is StatusEnum.DISABLE
    assert StatusEnum.get_by_label(" 关闭 ") is None
    assert StatusEnum.get_by_label([]) is None
    assert ChannelEnum.from_code("web") is ChannelEnum.WEB

    choices = StatusEnum.choices()
    assert choices == [(0, "关闭"), (1, "开启")]
    choices.clear()
    assert len(StatusEnum.choices()) == 2


@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, [], {}, ForeignIntEnum.VALUE, 99])
def test_integer_boundary_rejects_coercion_and_unknown_values(value: object):
    assert StatusEnum.get_by_code(value) is None
    with pytest.raises(ValueError, match="编码无效"):
        StatusEnum.from_code(value)
    with pytest.raises(ValidationError):
        TypeAdapter(StrictStatus).validate_python(value)


@pytest.mark.parametrize("value", [b"web", " web ", "WEB", "网页", ForeignStrEnum.VALUE])
def test_string_boundary_does_not_normalize_or_accept_foreign_members(value: object):
    assert ChannelEnum.get_by_code(value) is None
    with pytest.raises(ValidationError):
        TypeAdapter(StrictChannel).validate_python(value)


@pytest.mark.parametrize(
    ("members", "error"),
    [
        ({"A": (1, "甲"), "B": (1, "乙")}, ValueError),
        ({"A": (1, "甲"), "B": (2, "甲")}, ValueError),
        ({"A": (1, "甲"), "B": ("two", "乙")}, TypeError),
        ({"A": (True, "甲")}, TypeError),
        ({"A": (1.0, "甲")}, TypeError),
        ({"A": ([], "甲")}, TypeError),
        ({"A": ("", "甲")}, ValueError),
        ({"A": (" a ", "甲")}, ValueError),
        ({"A": (1, " ")}, ValueError),
        ({"A": (1, 2)}, TypeError),
    ],
)
def test_invalid_definitions_fail_at_class_creation(members, error):
    with pytest.raises(error):
        BaseEnum("InvalidEnum", members)


def test_error_message_does_not_echo_external_value():
    with pytest.raises(ValueError) as error:
        ChannelEnum.from_code("private-input-do-not-echo")
    assert "private-input" not in str(error.value)


def test_pydantic_preserves_members_in_python_and_codes_in_json():
    payload = Payload.model_validate({"status": 0, "channel": "web"})
    assert payload.model_dump() == {"status": StatusEnum.DISABLE, "channel": ChannelEnum.WEB}
    assert payload.model_dump(mode="json") == {"status": 0, "channel": "web"}
    assert Payload.model_validate_json(payload.model_dump_json()) == payload
    assert (
        Payload.model_validate({"status": 1, "channel": "app"}, strict=True).status
        is StatusEnum.ENABLE
    )

    with pytest.raises(ValidationError):
        Payload.model_validate_json('{"status":true,"channel":"web"}')


def test_native_constructor_and_unannotated_pydantic_keep_standard_behavior():
    # 原生 Enum 会把 True 匹配到 1；需要区分时必须使用 from_code。
    assert StatusEnum(True) is StatusEnum.ENABLE
    assert TypeAdapter(StatusEnum).validate_python(True) is StatusEnum.ENABLE


async def test_fastapi_contract_exposes_codes_and_rejects_invalid_json():
    application = FastAPI()

    @application.post("/enum-check", response_model=Payload)
    async def echo(payload: Payload) -> Payload:
        return payload

    schemas = application.openapi()["components"]["schemas"]
    assert schemas["StatusEnum"]["type"] == "integer"
    assert schemas["StatusEnum"]["enum"] == [0, 1]
    assert schemas["ChannelEnum"]["type"] == "string"
    assert schemas["ChannelEnum"]["enum"] == ["web", "app"]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.post("/enum-check", json={"status": 0, "channel": "web"})
        assert response.status_code == 200
        assert response.json() == {"status": 0, "channel": "web"}
        for invalid in (True, 1.0, "1", 99):
            response = await client.post("/enum-check", json={"status": invalid, "channel": "web"})
            assert response.status_code == 422
