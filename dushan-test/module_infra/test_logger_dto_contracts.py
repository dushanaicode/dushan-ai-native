from datetime import datetime

import pytest
from pydantic import ValidationError

from module_infra.spi.logger.dto.api_access_log_create_req_dto import ApiAccessLogCreateReqDTO
from module_infra.spi.logger.dto.api_error_log_create_req_dto import ApiErrorLogCreateReqDTO

ACCESS_VALUES = {
    "application_name": "test-app",
    "request_method": "GET",
    "request_url": "/items",
    "user_ip": "",
    "user_agent": "",
    "begin_time": datetime(2026, 10, 6),
    "end_time": datetime(2026, 10, 6),
    "duration": 0,
    "result_code": 0,
}
ERROR_VALUES = {
    "application_name": "test-app",
    "request_method": "GET",
    "request_url": "/items",
    "request_params": {},
    "user_ip": "",
    "user_agent": "",
    "exception_time": datetime(2026, 10, 6),
    "exception_name": "RuntimeError",
    "exception_message": "",
    "exception_root_cause_message": "",
    "exception_stack_trace": "",
    "exception_class_name": "builtins",
    "exception_file_name": "",
    "exception_method_name": "",
    "exception_line_number": 0,
    "trace_id": "",
}


@pytest.mark.parametrize(
    ("dto_type", "values"),
    [(ApiAccessLogCreateReqDTO, ACCESS_VALUES), (ApiErrorLogCreateReqDTO, ERROR_VALUES)],
)
def test_logger_dtos_preserve_valid_empty_and_zero_values(dto_type, values):
    """空串、空字典和零值继续表达匿名请求及无异常栈信息。"""
    dto = dto_type(**values)
    assert dto.model_dump(include=set(values)) == values
    assert dto.user_id is None
    assert dto.tenant_id is None


@pytest.mark.parametrize(
    ("dto_type", "values", "field"),
    [
        (dto_type, values, field)
        for dto_type, values in (
            (ApiAccessLogCreateReqDTO, ACCESS_VALUES),
            (ApiErrorLogCreateReqDTO, ERROR_VALUES),
        )
        for field in values
    ],
)
def test_logger_required_fields_reject_none_with_native_type_error(dto_type, values, field):
    """必填字段由声明类型拒绝 None，并定位到原字段。"""
    with pytest.raises(ValidationError) as error:
        dto_type(**(values | {field: None}))
    details = error.value.errors(include_url=False)
    assert len(details) == 1
    assert details[0]["loc"] == (field,)
    assert details[0]["type"].endswith("_type")


def test_error_request_params_are_required_and_reject_none_assignment():
    """请求参数必须显式传字典，构造与赋值使用同一契约。"""
    values = {key: value for key, value in ERROR_VALUES.items() if key != "request_params"}
    with pytest.raises(ValidationError) as missing:
        ApiErrorLogCreateReqDTO(**values)
    assert missing.value.errors()[0]["type"] == "missing"
    assert missing.value.errors()[0]["loc"] == ("request_params",)

    dto = ApiErrorLogCreateReqDTO(**ERROR_VALUES)
    with pytest.raises(ValidationError) as invalid:
        dto.request_params = None
    assert invalid.value.errors()[0]["type"] == "dict_type"


@pytest.mark.parametrize(
    ("dto_type", "values", "field", "limit"),
    [
        (ApiAccessLogCreateReqDTO, ACCESS_VALUES, "result_msg", 512),
        (ApiErrorLogCreateReqDTO, ERROR_VALUES, "exception_message", 512),
        (ApiErrorLogCreateReqDTO, ERROR_VALUES, "exception_root_cause_message", 512),
        (ApiErrorLogCreateReqDTO, ERROR_VALUES, "exception_stack_trace", 2048),
    ],
)
@pytest.mark.parametrize("as_bytes", [False, True])
def test_logger_messages_truncate_after_text_validation(dto_type, values, field, limit, as_bytes):
    """字符串及合法 UTF-8 字节解码后都按字符截断，赋值时同样生效。"""
    message = "异常" * (limit + 1)
    value = message.encode() if as_bytes else message
    dto = dto_type(**(values | {field: value}))
    assert getattr(dto, field) == message[:limit]
    setattr(dto, field, value)
    assert getattr(dto, field) == message[:limit]


@pytest.mark.parametrize("message", [None, "", "正常提示"])
def test_access_log_keeps_optional_result_message(message):
    """访问日志允许省略结果提示，并保留已提供的短文本。"""
    assert ApiAccessLogCreateReqDTO(**ACCESS_VALUES).result_msg is None
    assert ApiAccessLogCreateReqDTO(**ACCESS_VALUES, result_msg=message).result_msg == message
