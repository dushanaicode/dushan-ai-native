from asyncio import CancelledError
from dataclasses import FrozenInstanceError
from http import HTTPStatus
from importlib import import_module
from typing import Any

import pytest
from fastapi import HTTPException

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.auth_exception import AuthException
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)
from framework.common.exception.exceptions.configuration_exception import (
    ConfigurationException,
)
from framework.common.exception.exceptions.conflict_exception import ConflictException
from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.exception.exceptions.model_validator_exception import (
    ModelValidatorException,
)
from framework.common.exception.exceptions.not_found_exception import NotFoundException
from framework.common.exception.exceptions.permission_exception import (
    PermissionException,
)
from framework.common.exception.exceptions.rate_limit_exception import (
    RateLimitException,
)
from framework.common.exception.exceptions.remote_error_detail import RemoteErrorDetail
from framework.common.exception.exceptions.remote_service_exception import RemoteServiceException
from framework.common.exception.exceptions.server_exception import ServerException
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.exception.exceptions.third_party_exception import ThirdPartyException
from framework.common.exception.registry.error_code_decorator import error_code
from framework.common.exception.registry.error_code_registry import ErrorCodeRegistry
from framework.common.exception.utils.exception_util import ExceptionUtil
from framework.common.exception.utils.response_builder import ExceptionResponseBuilder
from framework.common.security.sanitizer import Sanitizer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("overrides", "failure"),
    [
        ({"code": True}, TypeError),
        ({"code": "1000"}, TypeError),
        ({"description": " "}, ValueError),
        ({"message_key": None}, TypeError),
        ({"http_status": True}, TypeError),
        ({"http_status": 400.0}, TypeError),
        ({"http_status": 600}, ValueError),
    ],
)
def test_error_code_rejects_invalid_definitions(overrides, failure) -> None:
    """定义阶段拒绝隐式类型转换、空文案和非法传输状态。"""
    arguments = {"code": 1000, "description": "默认提示", "message_key": "error.test"}
    with pytest.raises(failure):
        ErrorCode(**(arguments | overrides))


def test_registry_keeps_query_conflict_checks_and_native_raising() -> None:
    """注册器保留查询和冲突检查，调用方用原生条件抛出参数化业务异常。"""

    @error_code
    class ExampleCodes:
        MISSING = ErrorCode(code=1000, description="资源 {} 不存在", message_key="resource.missing")

    try:
        ErrorCodeRegistry.register_all([GlobalErrorCodeConstants, ExampleCodes])
        assert ErrorCodeRegistry.is_initialized()
        assert ErrorCodeRegistry.get_by_code(1000) is ExampleCodes.MISSING
        assert ErrorCodeRegistry.get_all()[1000] is ExampleCodes.MISSING
        assert ErrorCodeRegistry.get_all_detail()[1000][:2] == ("ExampleCodes", "MISSING")
        with pytest.raises(ConfigurationException):
            ErrorCodeRegistry.register_class(ExampleCodes)
        value = 0
        if value is None:
            raise ServiceException(ExampleCodes.MISSING, "示例")
        assert value == 0
        with pytest.raises(ServiceException) as captured:
            missing = True
            if missing:
                raise ServiceException(ExampleCodes.MISSING, "示例")
        assert captured.value.msg == "资源 示例 不存在"
    finally:
        ErrorCodeRegistry.reset()


def test_error_code_is_immutable_and_can_change_message_key() -> None:
    """修改翻译键会创建新定义，不会改动共享错误码。"""
    error_code = ErrorCode(
        code=1001,
        description="test failure",
        message_key="error.old",
        http_status=HTTPStatus.CONFLICT,
    )

    changed = error_code.with_message_key("error.new")

    assert changed.code == error_code.code
    assert changed.description == error_code.description
    assert changed.message_key == "error.new"
    assert changed.http_status == HTTPStatus.CONFLICT
    assert error_code.message_key == "error.old"
    with pytest.raises(FrozenInstanceError):
        error_code.code = 2


def test_base_business_exception_formats_explicit_message() -> None:
    """显式提示使用位置参数，同时保留翻译键和上下文。"""
    error_code = ErrorCode(code=2001, description="fallback", message_key="error.test")
    exc = BaseBusinessException(
        error_code=error_code,
        msg="entity {} failed",
        format_args=["user"],
        context={"id": 1},
    )

    assert exc.error_code is error_code
    assert exc.msg == "entity user failed"
    assert exc.message_key == "error.test"
    assert exc.context == {"id": 1}
    assert exc.format_args == ["user"]


def test_error_code_http_status_overrides_exception_class_default() -> None:
    """错误码指定的 HTTP 状态优先于异常类默认值。"""
    error_code = ErrorCode(
        code=2002,
        description="unauthorized",
        message_key="error.unauthorized",
        http_status=HTTPStatus.UNAUTHORIZED,
    )

    exc = BaseBusinessException(error_code=error_code)

    assert exc.http_status == HTTPStatus.UNAUTHORIZED


def test_base_business_exception_rejects_negative_retry_after_and_accepts_zero() -> None:
    """显式重试等待时间不能为负数，零秒可以原样保留。"""
    error_code = GlobalErrorCodeConstants.TOO_MANY_REQUESTS

    with pytest.raises(ValueError, match="retry_after 不能为负数"):
        BaseBusinessException(error_code, retry_after=-1)

    assert BaseBusinessException(error_code, retry_after=0).retry_after == 0


def test_rate_limit_exception_validates_retry_after_class_default() -> None:
    """限流子类的默认等待时间同样不能为负数，零秒会保留在响应中。"""

    class InvalidRateLimitException(RateLimitException):
        retry_after = -1

    class ImmediateRateLimitException(RateLimitException):
        retry_after = 0

    with pytest.raises(ValueError, match="retry_after 不能为负数"):
        InvalidRateLimitException()

    exc = ImmediateRateLimitException()
    assert exc.retry_after == 0
    response = ExceptionResponseBuilder.build(exc.error_code, exc.msg, exc=exc)
    assert response["retry_after"] == 0


def test_base_business_exception_uses_default_when_format_args_mismatch() -> None:
    """参数不足时回退默认提示，并清空会让翻译层再次失败的参数。"""
    error_code = ErrorCode(code=2002, description="fallback", message_key="error.test")

    exc = BaseBusinessException(error_code=error_code, msg="{} {}", format_args=["one"])

    assert exc.msg == error_code.description
    assert exc.format_args == []


def test_service_exception_records_format_args_with_default_msg() -> None:
    """服务异常保留位置参数供翻译，并使用默认提示。"""
    error_code = ErrorCode(code=3001, description="service failed", message_key="error.service")

    exc = ServiceException(error_code, "alpha")

    assert isinstance(exc, BaseBusinessException)
    assert exc.error_code is error_code
    assert exc.format_args == ["alpha"]
    assert exc.msg == error_code.description

    parameterized = ErrorCode(
        code=3002, description="服务 {} 不可用", message_key="error.service_unavailable"
    )
    assert ServiceException(parameterized, "report").msg == "服务 report 不可用"


def test_specific_exception_defaults_use_global_error_codes() -> None:
    """常用异常子类采用各自对应的全局错误定义。"""
    assert AuthException().error_code is GlobalErrorCodeConstants.UNAUTHORIZED
    assert PermissionException().error_code is GlobalErrorCodeConstants.FORBIDDEN
    assert NotFoundException().error_code is GlobalErrorCodeConstants.NOT_FOUND
    assert IllegalArgumentException().error_code is GlobalErrorCodeConstants.BAD_REQUEST
    assert ModelValidatorException().error_code is GlobalErrorCodeConstants.VALIDATION_ERROR


def test_model_validator_exception_is_value_error() -> None:
    """模型校验异常仍可被 Pydantic 作为 ValueError 处理。"""
    exc = ModelValidatorException(msg="invalid")

    assert isinstance(exc, ValueError)
    assert exc.msg == "invalid"


def test_exception_util_maps_http_like_errors_and_sanitizes_messages() -> None:
    """HTTP 类异常按状态映射错误码，并清理消息中的敏感信息。"""
    exc = HTTPException(status_code=404, detail="token=abc")

    assert ExceptionUtil.get_error_code(exc) is GlobalErrorCodeConstants.NOT_FOUND
    assert ExceptionUtil.get_error_msg(exc) == "token=***"
    assert ExceptionUtil.get_message_key(exc) == GlobalErrorCodeConstants.NOT_FOUND.message_key
    assert (
        ExceptionUtil.get_error_code(RuntimeError("x"))
        is GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
    )
    assert (
        Sanitizer.sanitize_text("Authorization: Bearer abc.def token=raw") == "Authorization: ***"
    )


def test_global_error_code_values_are_stable() -> None:
    """保留公共错误编号，未知故障统一使用内部错误分类。"""
    assert GlobalErrorCodeConstants.SUCCESS.code == 0
    assert GlobalErrorCodeConstants.UNAUTHORIZED.code == 401
    assert GlobalErrorCodeConstants.FORBIDDEN.code == 403
    assert GlobalErrorCodeConstants.VALIDATION_ERROR.code == 422
    assert GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR.code == 500
    assert GlobalErrorCodeConstants.ERROR_CONFIGURATION.code == 502
    assert GlobalErrorCodeConstants.BAD_GATEWAY.code == 903
    assert not hasattr(GlobalErrorCodeConstants, "UNKNOWN_ERROR")
    assert not hasattr(GlobalErrorCodeConstants, "UNKNOWN")


def test_all_global_error_constants_are_error_codes_with_message_keys() -> None:
    """全局错误定义具备默认提示、翻译键、HTTP 状态且编号唯一。"""
    values = [
        value for value in vars(GlobalErrorCodeConstants).values() if isinstance(value, ErrorCode)
    ]

    assert values
    assert all(isinstance(value.code, int) for value in values)
    assert all(value.description for value in values)
    assert all(value.message_key.startswith("exception.") for value in values)
    assert all(value.http_status is not None for value in values)
    assert len({value.code for value in values}) == len(values)


@pytest.mark.parametrize("code", [-1, 0, 2**64])
def test_error_code_accepts_full_integer_range(code: int) -> None:
    """编号支持未知值和业务整数，不额外套用三十二位限制。"""
    assert ErrorCode(code=code, description="默认提示", message_key="test.failure").code == code


@pytest.mark.parametrize("code", [True, False, 400.0, "400", None, HTTPStatus.BAD_REQUEST])
def test_error_code_rejects_noninteger_codes(code: object) -> None:
    """布尔值、枚举和隐式转换值不能充当错误编号。"""
    with pytest.raises(TypeError):
        ErrorCode(code=code, description="默认提示", message_key="test.failure")


@pytest.mark.parametrize(
    ("template", "arguments"),
    [
        ("内部模板 {", ["private-value"]),
        ("内部模板 {:d}", ["private-value"]),
        ("内部模板 {missing}", ["private-value"]),
        ("内部模板 {} {}", ["private-value"]),
    ],
)
def test_invalid_format_uses_default_and_preserves_cause(template, arguments) -> None:
    """格式字符串错误不替换业务异常或原始原因，也不保留失败参数。"""
    original = RuntimeError("private-cause")
    definition = GlobalErrorCodeConstants.BAD_REQUEST
    exc = BaseBusinessException(definition, msg=template, format_args=arguments, cause=original)

    assert exc.msg == str(exc) == definition.description
    assert exc.args == (definition.description,)
    assert exc.__cause__ is original
    assert exc.error_code is definition
    assert exc.format_args == []
    assert "private" not in repr(exc)


@pytest.mark.parametrize("conversion", ["{}", "{!s}"])
def test_parameter_conversion_failure_keeps_business_exception(conversion: str) -> None:
    """参数自己的格式化和字符串转换失败时仍返回业务默认提示。"""

    class BrokenValue:
        def __format__(self, format_spec: str) -> str:
            """模拟参数格式化失败。"""
            raise RuntimeError("private-format-detail")

        def __str__(self) -> str:
            """模拟参数字符串转换失败。"""
            raise RuntimeError("private-string-detail")

    original = RuntimeError("private-cause")
    definition = GlobalErrorCodeConstants.BAD_REQUEST
    exc = BaseBusinessException(
        definition, msg=conversion, format_args=[BrokenValue()], cause=original
    )

    assert exc.msg == definition.description
    assert exc.__cause__ is original
    assert exc.format_args == []


@pytest.mark.parametrize("signal", [KeyboardInterrupt(), SystemExit(3), CancelledError()])
def test_formatting_preserves_control_signals(signal: BaseException) -> None:
    """格式参数触发取消或退出时继续传播原控制信号。"""

    class InterruptedValue:
        def __format__(self, format_spec: str) -> str:
            """在格式化时触发指定的控制异常。"""
            raise signal

    with pytest.raises(type(signal)) as captured:
        BaseBusinessException(
            GlobalErrorCodeConstants.BAD_REQUEST, msg="{}", format_args=[InterruptedValue()]
        )
    assert captured.value is signal


def test_all_exception_modules_are_importable() -> None:
    """所有异常模块可独立导入，不依赖数据库、业务服务或翻译器启动。"""
    modules = (
        "constants.global_error_code_constants",
        "core.error_code",
        "core.exception_handler",
        "core.exception_trace_reporter",
        "exceptions.auth_exception",
        "exceptions.base_business_exception",
        "exceptions.configuration_exception",
        "exceptions.conflict_exception",
        "exceptions.illegal_argument_exception",
        "exceptions.model_validator_exception",
        "exceptions.not_found_exception",
        "exceptions.permission_exception",
        "exceptions.rate_limit_exception",
        "exceptions.remote_service_exception",
        "exceptions.remote_error_detail",
        "exceptions.server_exception",
        "exceptions.service_exception",
        "exceptions.third_party_exception",
        "registry.error_code_decorator",
        "registry.error_code_registry",
        "utils.error_log_recorder",
        "utils.exception_logger",
        "utils.exception_util",
        "utils.response_builder",
    )
    for name in modules:
        import_module(f"framework.common.exception.{name}")


def test_configuration_exception_and_error_configuration_map_to_500() -> None:
    """本地配置错误使用 HTTP 500，网关错误使用 HTTP 502，两者编号分别为 502 和 903。"""
    assert (
        GlobalErrorCodeConstants.ERROR_CONFIGURATION.http_status == HTTPStatus.INTERNAL_SERVER_ERROR
    )
    assert GlobalErrorCodeConstants.ERROR_CONFIGURATION.code == 502
    assert ConfigurationException().http_status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert ConfigurationException().error_code.code == 502
    assert GlobalErrorCodeConstants.BAD_GATEWAY.http_status == HTTPStatus.BAD_GATEWAY
    assert GlobalErrorCodeConstants.BAD_GATEWAY.code == 903


def test_base_business_exception_record_error_strict_boolean() -> None:
    """record_error 必须是严格布尔值，禁止隐式类型转换。"""
    error_code = ErrorCode(code=2003, description="strict bool", message_key="error.test")
    with pytest.raises(TypeError, match="record_error 必须是布尔值"):
        BaseBusinessException(error_code=error_code, record_error="false")  # type: ignore[arg-type]

    exc = BaseBusinessException(error_code=error_code, record_error=True)
    assert exc.record_error is True

    exc_default = BaseBusinessException(error_code=error_code)
    assert exc_default.record_error is False


@pytest.mark.parametrize("class_default", ["false", 1])
def test_record_error_rejects_invalid_class_default_unless_explicitly_overridden(
    class_default: Any,
) -> None:
    """非法子类默认值会被拒绝，显式 False 可以覆盖该默认值。"""

    class InvalidRecordException(BaseBusinessException):
        record_error = class_default

    error_code = GlobalErrorCodeConstants.BAD_REQUEST
    with pytest.raises(TypeError, match="record_error 必须是布尔值"):
        InvalidRecordException(error_code)

    assert InvalidRecordException(error_code, record_error=False).record_error is False


def test_record_error_true_class_default_can_be_explicitly_disabled() -> None:
    """有效的子类默认值会生效，显式 False 仍可关闭记录。"""

    class RecordedBusinessException(BaseBusinessException):
        record_error = True

    error_code = GlobalErrorCodeConstants.BAD_REQUEST
    assert RecordedBusinessException(error_code).record_error is True
    assert RecordedBusinessException(error_code, record_error=False).record_error is False


def test_subclass_default_error_code_does_not_replace_invalid_explicit_values() -> None:
    """只有省略或传入 None 才采用子类默认定义，错误类型和成功码仍被拒绝。"""
    with pytest.raises(TypeError):
        BaseBusinessException()

    class ResourceConflict(BaseBusinessException):
        default_error_code = GlobalErrorCodeConstants.CONFLICT

    assert ResourceConflict().error_code is GlobalErrorCodeConstants.CONFLICT
    assert ResourceConflict(None).error_code is GlobalErrorCodeConstants.CONFLICT
    with pytest.raises(TypeError):
        ResourceConflict(False)
    with pytest.raises(ValueError):
        ResourceConflict(GlobalErrorCodeConstants.SUCCESS)


@pytest.mark.parametrize(
    ("exception_type", "default_error"),
    [
        (AuthException, GlobalErrorCodeConstants.UNAUTHORIZED),
        (PermissionException, GlobalErrorCodeConstants.FORBIDDEN),
        (NotFoundException, GlobalErrorCodeConstants.NOT_FOUND),
        (IllegalArgumentException, GlobalErrorCodeConstants.BAD_REQUEST),
        (ModelValidatorException, GlobalErrorCodeConstants.VALIDATION_ERROR),
        (ConflictException, GlobalErrorCodeConstants.CONFLICT),
        (ConfigurationException, GlobalErrorCodeConstants.ERROR_CONFIGURATION),
        (RateLimitException, GlobalErrorCodeConstants.TOO_MANY_REQUESTS),
        (ServerException, GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR),
        (ThirdPartyException, GlobalErrorCodeConstants.SERVICE_UNAVAILABLE),
        (RemoteServiceException, GlobalErrorCodeConstants.SERVICE_UNAVAILABLE),
    ],
)
def test_exception_subclasses_accept_shared_metadata(exception_type, default_error) -> None:
    """所有子类使用统一元数据入口，并允许显式错误定义和 HTTP 状态覆盖默认值。"""
    original = RuntimeError("private-cause")
    failure = exception_type(
        msg="资源 {} 不可用",
        message_key="resource.unavailable",
        cause=original,
        context={"id": 7},
        format_args=(7,),
        retry_after=0,
        record_error=True,
    )
    assert failure.error_code is default_error
    assert failure.http_status == default_error.http_status
    assert failure.msg == "资源 7 不可用"
    assert failure.message_key == "resource.unavailable"
    assert failure.__cause__ is original
    assert failure.context == {"id": 7}
    assert failure.retry_after == 0
    assert failure.record_error is True
    assert "private-cause" not in str(failure)

    override = ErrorCode(
        code=7010, description="自定义业务失败", message_key="custom.failure", http_status=409
    )
    assert exception_type(override).http_status == 409
    explicit = exception_type(override, http_status=503, record_error=False)
    assert explicit.error_code is override
    assert explicit.http_status == 503
    assert explicit.record_error is False


def test_service_exception_keeps_format_arguments_and_keyword_metadata() -> None:
    """服务异常的位置参数只用于文案，原始原因和重试信息明确通过关键字传递。"""
    definition = ErrorCode(code=7001, description="服务 {} 失败", message_key="service.failure")
    original = RuntimeError("private-cause")
    failure = ServiceException(
        definition,
        "report",
        cause=original,
        context={"service": "report"},
        message_key="custom.service_failure",
        http_status=503,
        retry_after=3,
        record_error=True,
    )
    assert failure.msg == "服务 report 失败"
    assert failure.format_args == ["report"]
    assert failure.__cause__ is original
    assert failure.context == {"service": "report"}
    assert failure.message_key == "custom.service_failure"
    assert failure.http_status == 503
    assert failure.retry_after == 3
    assert failure.record_error is True


def test_remote_detail_is_keyword_only_and_not_public_response_data() -> None:
    """远程详情从独立模块导入，仅作为内部排错信息，不自动进入公开响应。"""
    detail = RemoteErrorDetail(service="billing", raw={"token": "private-upstream"})
    original = RuntimeError("private-cause")
    failure = RemoteServiceException(detail=detail, cause=original, retry_after=4)
    assert failure.detail is detail
    assert failure.__cause__ is original
    assert failure.retryable is True
    assert failure.retry_after == 4
    assert "private-upstream" not in repr(
        ExceptionResponseBuilder.build(failure.error_code, failure.msg, exc=failure)
    )
    with pytest.raises(TypeError):
        RemoteServiceException(None, None, detail)
    with pytest.raises(TypeError):
        AuthException(None, None, "auth.error")


@pytest.mark.parametrize("retry_after", [True, "1", 1.0, -1])
def test_subclass_retry_guards_cannot_be_bypassed(retry_after) -> None:
    """继承得到的重试入口仍拒绝布尔值、隐式数值转换和负数。"""
    with pytest.raises((TypeError, ValueError)):
        RateLimitException(retry_after=retry_after)


def test_http_default_mapping_matches_transport_status_without_overwriting_configuration() -> None:
    """HTTP 默认分类与传输状态一致，本地配置错误保留独立业务编号。"""
    mapping = ExceptionUtil._STATUS_CODE_TO_ERROR_CODE
    assert mapping
    assert all(status == definition.http_status for status, definition in mapping.items())
    for status, definition in mapping.items():
        assert ExceptionUtil.get_error_code(HTTPException(status_code=status)) is definition
    assert mapping[413] is GlobalErrorCodeConstants.PAYLOAD_TOO_LARGE
    assert mapping[423] is GlobalErrorCodeConstants.LOCKED
    assert mapping[500] is GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
    assert mapping[502] is GlobalErrorCodeConstants.BAD_GATEWAY
    assert GlobalErrorCodeConstants.ERROR_CONFIGURATION.http_status == 500
    assert ExceptionUtil.get_error_code(
        HTTPException(status_code=599, detail="未定义的服务状态")
    ) is (GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR)
