from datetime import datetime, timezone
from typing import Annotated, ClassVar

import pytest
from pydantic import Field, SecretStr, StringConstraints, ValidationError

from framework.common.schemas.base_bo import BaseBO
from framework.common.schemas.base_dto import BaseDTO
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.schemas.base_vo import BaseVO


class ContactResponse(BaseVO):
    display_name: str
    mobile: str
    created_at: datetime
    internal_secret: str = Field(default="private", exclude=True)


class ContactPatch(BaseRequestVO):
    masked_patterns: ClassVar[dict[str, str]] = {"mobile": r"\d{3}\*{4}\d{4}"}
    display_name: str | None = None
    mobile: str | None = None
    department_label: str | None = None


def test_response_preserves_whitespace_masked_display_and_excluded_fields():
    """响应模型不把展示掩码或空格误当成需要修复的输入。"""
    model = ContactResponse(
        displayName=" Alice ",
        mobile="138****8000",
        createdAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    data = model.to_response()
    assert data == {
        "displayName": " Alice ",
        "mobile": "138****8000",
        "createdAt": "2026-01-01T00:00:00Z",
    }
    assert ContactResponse.list_to_response([model]) == [data]


def test_request_distinguishes_unset_explicit_none_and_write_whitelist():
    """PATCH 的省略和清空保持区别，跨表展示字段不因输入存在就进入写入集合。"""
    omitted = ContactPatch(departmentLabel="运营部")
    assert omitted.to_write_dict(fields={"mobile", "display_name"}) == {}
    explicit = ContactPatch(mobile=None, departmentLabel="运营部")
    assert explicit.to_write_dict(fields={"mobile", "display_name"}) == {"mobile": None}
    assert explicit.to_write_dict(fields=set()) == {}
    with pytest.raises(ValueError, match="Python 字段名"):
        explicit.to_write_dict(fields={"displayName"})


def test_masked_request_is_rejected_instead_of_changed_to_none():
    """掩码输入产生校验错误，正常值不被改变，赋值失败也不破坏旧值。"""
    with pytest.raises(ValidationError, match="脱敏占位值"):
        ContactPatch(mobile="138****8000")
    model = ContactPatch(mobile="13812348000")
    with pytest.raises(ValidationError):
        model.mobile = "138****8000"
    assert model.mobile == "13812348000"
    assert model.to_write_dict(fields={"mobile"}) == {"mobile": "13812348000"}


def test_required_field_remains_required_and_non_nullable():
    """必填字符串不能被防回写逻辑变成 None 或未提供。"""

    class RequiredRequest(BaseRequestVO):
        masked_patterns: ClassVar[dict[str, str]] = {"phone_number": r"\d{3}\*{4}\d{4}"}
        phone_number: str

    for payload in ({}, {"phoneNumber": None}, {"phoneNumber": "138****8000"}):
        with pytest.raises(ValidationError):
            RequiredRequest(**payload)
    valid = RequiredRequest(phoneNumber="13812348000")
    assert valid.phone_number == "13812348000"
    assert valid.model_fields_set == {"phone_number"}


def test_secret_input_uses_full_mask_pattern_without_rejecting_normal_asterisk():
    """SecretStr 同样检查占位值，正常含星号的内容保持原值。"""

    class SecretRequest(BaseRequestVO):
        masked_patterns: ClassVar[dict[str, str]] = {"token": r"\*{6,}"}
        token: SecretStr

    with pytest.raises(ValidationError, match="脱敏占位值"):
        SecretRequest(token="********")
    assert SecretRequest(token="real*value").token.get_secret_value() == "real*value"


def test_mask_strategy_does_not_leak_between_request_models():
    """每个请求类持有自己的只读策略，不改变其他类型。"""

    class UnmaskedRequest(BaseRequestVO):
        mobile: str

    assert UnmaskedRequest(mobile="138****8000").mobile == "138****8000"
    with pytest.raises(TypeError):
        ContactPatch.masked_patterns["other"] = "*"
    assert not BaseRequestVO.masked_patterns
    assert not UnmaskedRequest.masked_patterns


@pytest.mark.parametrize("patterns", [{"missing": "x"}, {"mobile": ""}, {"mobile": "["}])
def test_invalid_mask_strategy_fails_when_model_is_defined(patterns):
    """错误字段名或表达式在定义阶段失败，避免请求时静默失去保护。"""
    with pytest.raises(ValueError):

        class InvalidRequest(BaseRequestVO):
            masked_patterns: ClassVar[dict[str, str]] = patterns
            mobile: str


def test_trim_is_explicit_on_the_field():
    """展示名称可单独去空格，旁边的空格敏感字段不会被全局改写。"""

    class TextRequest(BaseRequestVO):
        display_name: Annotated[str, StringConstraints(strip_whitespace=True)]
        raw_text: str

    model = TextRequest(displayName=" Alice ", rawText=" keep ")
    assert model.display_name == "Alice"
    assert model.raw_text == " keep "


@pytest.mark.parametrize("base", [BaseVO, BaseRequestVO, BaseDTO, BaseBO])
def test_schema_rejects_unknown_fields_and_invalid_assignment(base):
    """统一拒绝未知字段，字段修改仍遵循原模型类型。"""

    class Record(base):
        record_id: int

    with pytest.raises(ValidationError):
        Record(record_id=1, unknown=True)
    record = Record(record_id=1)
    with pytest.raises(ValidationError):
        record.record_id = "invalid"
    assert record.record_id == 1


def test_runtime_objects_are_internal_and_attributes_remain_supported():
    """BO 可容纳运行时对象，DTO和VO从对象读取已声明字段。"""

    class RuntimeHandle:
        pass

    class Command(BaseBO):
        handle: RuntimeHandle

    class RecordDTO(BaseDTO):
        record_id: int

    class RecordVO(BaseVO):
        record_id: int

    class Record:
        record_id = 7

    handle = RuntimeHandle()
    assert Command(handle=handle).handle is handle
    assert RecordDTO.model_validate(Record()).record_id == 7
    assert RecordVO.model_validate(Record()).to_response() == {"recordId": 7}
