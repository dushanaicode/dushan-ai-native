from decimal import Decimal
from enum import Enum
from typing import Annotated

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AfterValidator, field_validator
from pydantic_core import PydanticCustomError

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.core.exception_handler import GlobalExceptionHandler
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.allowed_values import AllowedValues
from framework.common.validator.assert_true import AssertTrue
from framework.common.validator.bank_card import BankCard
from framework.common.validator.datetime_format import DateTimeFormat
from framework.common.validator.decimal_min import DecimalMin
from framework.common.validator.dict_keys import DictKeys
from framework.common.validator.email import Email
from framework.common.validator.id_card import IDCard
from framework.common.validator.in_enum import InEnum
from framework.common.validator.ipv4 import IPV4
from framework.common.validator.is_json import IsJSON
from framework.common.validator.length import Length
from framework.common.validator.min import Min
from framework.common.validator.min_max_value import MinMaxValue
from framework.common.validator.mobile import Mobile
from framework.common.validator.not_blank import NotBlank
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.pattern import Pattern
from framework.common.validator.positive_or_zero import PositiveOrZero
from framework.common.validator.range import Range
from framework.common.validator.size import Size
from framework.common.validator.unique_items import UniqueItems
from framework.common.validator.url import URL

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "validate,value",
    [
        (lambda v: NotNull.require_not_null("值", v), 0),
        (lambda v: NotNull.require_not_null("值", v), False),
        (lambda v: NotBlank.require_not_blank("名称", v), " name "),
        (lambda v: NotEmpty.require_not_empty("列表", v), [0]),
        (lambda v: AssertTrue.require_true("同意", v), True),
        (lambda v: Size.require_size("长度", v, 0, 2), ""),
        (lambda v: Length.require_length("名称", v, 1, 2), "渡山"),
        (lambda v: Min.require_min("数量", v, 2), 2.5),
        (lambda v: MinMaxValue.require_min_max("数量", v, 0, 2), 2),
        (lambda v: Range.require_range("数量", v, 0, 2), Decimal("1.01")),
        (lambda v: PositiveOrZero.require_positive_or_zero("数量", v), 0),
        (lambda v: DecimalMin.require_decimal_min("金额", v, Decimal("0.1")), Decimal("0.1")),
        (lambda v: AllowedValues.require_allowed_values("范围", v, {"a", "b"}), ["b", "a"]),
        (lambda v: DictKeys.require_allowed_keys("对象", v, frozenset({"x"})), {"x": 0}),
        (lambda v: UniqueItems.require_unique("范围", v), [2, 1]),
        (lambda v: InEnum.require_in_enum("状态", v, StatusEnum), 1),
        (lambda v: Pattern.require_pattern("编码", v, r"[a-z]+"), "abc"),
        (lambda v: BankCard.require_bank_card("卡号", v), "4532015112830366"),
        (lambda v: IDCard.require_id_card("证件", v), "11010519491231002x"),
        (lambda v: Email.require_email("邮箱", v), "a+b@example.com"),
        (lambda v: Mobile.require_mobile("电话", v), "13800138000"),
        (lambda v: IPV4.require_ipv4("地址", v), "192.168.1.1"),
        (lambda v: IsJSON.require_json("配置", v), '{"enabled":false}'),
        (lambda v: URL.require_url("地址", v), "https://example.com/path#part"),
        (lambda v: URL.require_url("地址", v), "http://[::1]:8000/"),
        (lambda v: DateTimeFormat.require_datetime_format("日期", v, ["%Y-%m-%d"]), "2024-02-29"),
    ],
)
def test_validators_keep_valid_values(validate, value):
    assert validate(value) == value


@pytest.mark.parametrize(
    "validate,value",
    [
        (lambda v: NotNull.require_not_null("值", v), None),
        (lambda v: NotBlank.require_not_blank("名称", v), " "),
        (lambda v: NotBlank.require_not_blank("名称", v), 1),
        (lambda v: NotEmpty.require_not_empty("集合", v), []),
        (lambda v: NotEmpty.require_not_empty("集合", v), 1),
        (lambda v: AssertTrue.require_true("同意", v), 1),
        (lambda v: AssertTrue.require_true("同意", v), "true"),
        (lambda v: Size.require_size("长度", v, min_length=1), ""),
        (lambda v: Size.require_size("长度", v, min_length=1), 7),
        (lambda v: Length.require_length("长度", v, 1, 2), [1]),
        (lambda v: Min.require_min("数量", v, 2), "3"),
        (lambda v: MinMaxValue.require_min_max("数量", v, 0, 2), 3),
        (lambda v: Range.require_range("数量", v, 0, 2), True),
        (lambda v: Range.require_range("数量", v, 0, 2), float("nan")),
        (lambda v: PositiveOrZero.require_positive_or_zero("数量", v), float("inf")),
        (lambda v: PositiveOrZero.require_positive_or_zero("数量", v), -1),
        (lambda v: DecimalMin.require_decimal_min("金额", v, 0), Decimal("NaN")),
        (lambda v: DecimalMin.require_decimal_min("金额", v, 0), "1"),
        (lambda v: DecimalMin.require_decimal_min("金额", v, 1, inclusive=False), Decimal("1")),
        (lambda v: AllowedValues.require_allowed_values("范围", v, {"a"}), ["b"]),
        (lambda v: DictKeys.require_allowed_keys("对象", v, frozenset({"x"})), {1: "bad"}),
        (lambda v: UniqueItems.require_unique("范围", v), [1, 1]),
        (lambda v: InEnum.require_in_enum("状态", v, StatusEnum), True),
        (lambda v: InEnum.require_in_enum("状态", v, StatusEnum), 1.0),
        (lambda v: InEnum.require_in_enum("状态", v, StatusEnum), "1"),
        (lambda v: Pattern.require_pattern("编码", v, r"[a-z]+"), "abc9"),
        (lambda v: BankCard.require_bank_card("卡号", v), "4532015112830367"),
        (lambda v: BankCard.require_bank_card("卡号", v), "４５３２０１５１１２８３０３６６"),
        (lambda v: IDCard.require_id_card("证件", v), "11010519490231002X"),
        (lambda v: IDCard.require_id_card("证件", v), "110105194912310021"),
        (lambda v: Email.require_email("邮箱", v), ""),
        (lambda v: Email.require_email("邮箱", v), "a..b@example.com"),
        (lambda v: Mobile.require_mobile("电话", v), "00000000000"),
        (lambda v: Mobile.require_mobile("电话", v), "１３８００１３８０００"),
        (lambda v: IPV4.require_ipv4("地址", v), "999.1.1.1"),
        (lambda v: IPV4.require_ipv4("地址", v), 123),
        (lambda v: IsJSON.require_json("配置", v), '{"x":1,"x":2}'),
        (lambda v: IsJSON.require_json("配置", v), "NaN"),
        (lambda v: URL.require_url("地址", v), "example.com"),
        (lambda v: URL.require_url("地址", v), "http://example.com:99999"),
        (lambda v: URL.require_url("地址", v), "http://user:secret@example.com"),
        (lambda v: URL.require_url("地址", v), "http://exam\nple.com"),
        (lambda v: DateTimeFormat.require_datetime_format("日期", v, ["%Y-%m-%d"]), "2023-02-29"),
    ],
)
def test_invalid_inputs_become_field_validation_errors(validate, value):
    with pytest.raises(PydanticCustomError):
        validate(value)


def test_optional_values_and_explicit_error_messages():
    assert Email.require_email("邮箱", None) is None
    assert Range.require_range("数量", None, min_value=0) is None
    assert NotNull.require_not_null("值", []) == []
    with pytest.raises(PydanticCustomError) as caught:
        NotBlank.require_not_blank("名称", "", error_msg="请填写名称")
    assert str(caught.value) == "请填写名称"
    with pytest.raises(ValueError):
        Size.require_size("名称", "abc", 4, 1)
    with pytest.raises(ValueError):
        Range.require_range("数量", 1)
    with pytest.raises(ValueError):
        Range.require_range("数量", 1, min_value=3, max_value=1)


def test_enum_values_do_not_depend_on_first_member_type():
    class Mixed(Enum):
        ONE = 1
        TEXT = "a"

    assert InEnum.require_in_enum("类型", "a", Mixed) == "a"


def test_datetime_ranges_validate_order_and_format():
    assert DateTimeFormat.parse_comma_separated_range(None, pattern="%Y-%m-%d") is None
    values = DateTimeFormat.parse_comma_separated_range("2024-02-29,2024-03-01", pattern="%Y-%m-%d")
    assert values[0].day == 29 and values[1].day == 1
    for text in ("", "2024-03-01,2024-02-29", "bad,bad", 123):
        with pytest.raises(PydanticCustomError):
            DateTimeFormat.parse_comma_separated_range(text, pattern="%Y-%m-%d")


class Contact(BaseRequestVO):
    mobile_number: str

    @field_validator("mobile_number")
    @classmethod
    def check_mobile(cls, value):
        return Mobile.require_mobile("手机号", value)


class Form(BaseRequestVO):
    contacts: list[Contact]
    agreed: Annotated[
        bool, AfterValidator(lambda value: AssertTrue.require_true("同意条款", value))
    ]


def test_fastapi_returns_all_nested_field_errors_without_echoing_input():
    app = FastAPI()
    GlobalExceptionHandler(debug=False).register(app)

    @app.post("/form")
    def submit(form: Form):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.post(
            "/form",
            json={"contacts": [{"mobileNumber": "password=private-value"}], "agreed": False},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] != 0
    assert {item["field"] for item in payload["error"]["fields"]} == {
        "contacts[0].mobileNumber",
        "agreed",
    }
    assert "private-value" not in response.text
    assert any("手机号" in item["message"] for item in payload["error"]["fields"])
