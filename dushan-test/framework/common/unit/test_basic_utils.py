import json

import pytest
from pydantic import BaseModel

from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.base_vo import BaseVO
from framework.common.utils.collection.conversion_utils import ConversionUtils
from framework.common.utils.json.json_utils import JsonUtils
from framework.common.utils.str.str_utils import StrUtils
from framework.common.utils.validation.validation_utils import ValidationUtils

pytestmark = pytest.mark.unit


class Person(BaseVO):
    user_name: str


def test_json_models_and_lists_preserve_structure():
    model = Person(user_name="渡山")
    assert json.loads(JsonUtils.to_json(model)) == {"userName": "渡山"}
    assert JsonUtils.parse_obj(b'{"userName":"alice"}', Person).user_name == "alice"
    assert JsonUtils.parse_list('[{"userName":"alice"}]', Person) == [Person(user_name="alice")]
    assert JsonUtils.to_json_bytes({"enabled": False}).decode("utf-8") == '{"enabled": false}'


@pytest.mark.parametrize("text", ["", "{bad}", '{"a":1,"a":2}', "NaN", "Infinity", "[1e400]"])
def test_json_rejects_ambiguous_or_invalid_input(text):
    assert JsonUtils.is_valid_json(text) is False
    with pytest.raises(ValueError):
        JsonUtils.parse_obj(text, dict)


def test_json_rejects_unknown_objects_and_keeps_falsey_paths():
    with pytest.raises(TypeError):
        JsonUtils.to_json({"object": object()})
    with pytest.raises(ValueError):
        JsonUtils.to_json({"value": float("nan")})
    for value in (0, False, "", [], None):
        assert JsonUtils.get_by_path({"a": {"b": value}}, "a.b") == value
    with pytest.raises(KeyError):
        JsonUtils.get_by_path({"a": {}}, "a.b")
    with pytest.raises(ValueError):
        JsonUtils.parse_obj("[]", dict)


def test_string_operations_do_not_hide_errors_or_override_keys():
    assert StrUtils.find_all_between("{{a}} {{b}}", "{{", "}}") == ["a", "b"]
    assert StrUtils.remove_line_contains("keep\ndrop me\nkeep2", "drop") == "keep\nkeep2"
    assert StrUtils.sub_before("user:1", ":", True) == "user:"
    assert StrUtils.to_int_list("1, 2,,3") == [1, 2, 3]
    assert StrUtils.to_int_set("1,1,2") == {1, 2}
    with pytest.raises(ValueError):
        StrUtils.to_int_list("1,bad")
    with pytest.raises(ValueError):
        StrUtils.deep_transform_keys({"user_name": 1, "userName": 2}, StrUtils.to_camel_case)
    assert StrUtils.to_snake_case("HTTPServer") == "http_server"
    assert StrUtils.escape_like(r"foo\%_") == r"foo\\\%\_"


@pytest.mark.parametrize("length", [0, 1, 2, 3, 5, 10])
def test_truncation_always_respects_maximum(length):
    assert len(StrUtils.truncate("abcdef", length)) <= length
    assert StrUtils.truncate("abcdef", 5) == "ab..."


def test_conversions_preserve_total_and_validated_fields():
    page = PageResult[dict](items=[{"user_name": "渡山", "private": "ignored"}], total=125)
    # 目标模型 extra=forbid 时不允许悄悄丢弃额外字段。
    with pytest.raises(ValueError):
        ConversionUtils.converter_do_to_vo(page, Person)
    page = PageResult[dict](items=[{"user_name": "渡山"}], total=125)
    converted = ConversionUtils.converter_do_to_vo(page, Person)
    assert converted.total == 125 and converted.items[0].user_name == "渡山"
    assert ConversionUtils.item_to_vo(None, Person) is None
    assert ConversionUtils.list_to_vo_list(iter(page.items), Person) == converted.items


def test_validation_utils_use_explicit_model_contract():
    class OptionalModel(BaseModel):
        name: str | None

    assert ValidationUtils.validate({"name": None}, OptionalModel).name is None
    assert ValidationUtils.validate_email("a@example.com")
    assert not ValidationUtils.is_xml_ncname("bad$name")
    assert ValidationUtils.is_xml_ncname("valid_name")
