import sys
import traceback
from asyncio import CancelledError

import pytest

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.diagnostics.terminal_error_reporter import TerminalErrorReporter

pytestmark = pytest.mark.unit


def test_sanitizer_sanitizes_basic_authorization_and_full_bearer_charset() -> None:
    """完整移除不同认证方案的凭据和 Bearer 内容。"""
    basic = Sanitizer.sanitize_text("Authorization: Basic dXNlcjpwYXNz==")
    digest = Sanitizer.sanitize_text(
        'Authorization: Digest username="alice", realm="api", nonce="N0NCE", response="RAW-RESPONSE"'
    )
    bearer = Sanitizer.sanitize_text("provider returned Bearer abc+def/ghi~jkl==")

    assert basic == "Authorization: ***"
    assert digest == "Authorization: ***"
    assert "dXNlcjpwYXNz" not in basic
    assert bearer == "provider returned Bearer ***"


def test_sanitizer_sanitizes_oauth_query_values() -> None:
    """清理授权回调和令牌 URL 中的敏感查询参数。"""
    raw_url = (
        "https://example.test/token?"
        "access_token=raw-access&client_secret=raw-secret&id_token=raw-id&code=raw-code&state=raw-state"
    )

    sanitized = Sanitizer.sanitize_text(raw_url)

    assert "raw-access" not in sanitized
    assert "raw-secret" not in sanitized
    assert "raw-id" not in sanitized
    assert "raw-code" not in sanitized
    assert "raw-state" not in sanitized
    assert "access_token=***" in sanitized
    assert "client_secret=***" in sanitized
    assert "id_token=***" in sanitized
    assert "code=***" in sanitized
    assert "state=***" in sanitized


@pytest.mark.parametrize(
    "serialized",
    [
        "{'access_token': 'super-secret'}",
        '{"password": "super-secret"}',
        '{"password": "abc\\"tail-secret", "safe": "value"}',
        "{'access_token': b'bytes-secret'}",
        '"access_token": {\n  "raw": "super-secret"\n}',
        '{"password": ("first-secret", "second-secret"), "safe": "value"}',
    ],
)
def test_sanitizer_sanitizes_quoted_mapping_values(serialized: str) -> None:
    """清理文本映射中的敏感值，包括嵌套和转义形式。"""
    sanitized = Sanitizer.sanitize_text(serialized)

    assert "super-secret" not in sanitized
    assert "***" in sanitized


def test_sanitizer_sanitizes_nested_sensitive_data() -> None:
    """递归清理结构化数据，并按需移除原始输入。"""
    payload = {
        "access-token": "secret",
        "clientSecret": "secret",
        "idToken": "token",
        "nested": ["password=secret", {"input": "raw", "safe": "value"}],
    }

    sanitized = Sanitizer.sanitize_sensitive_data(payload, redact_input=True)

    assert sanitized["access-token"] == "***"
    assert sanitized["clientSecret"] == "***"
    assert sanitized["idToken"] == "***"
    assert sanitized["nested"][0] == "password=***"
    assert sanitized["nested"][1]["input"] == "***"
    assert sanitized["nested"][1]["safe"] == "value"


@pytest.mark.parametrize(
    "field",
    [
        "set-cookie",
        "set_cookie",
        "setcookie",
        "身份证",
        "身份证号",
        "身份证号码",
        "access-token",
        "accessToken",
        "client-secret",
        "id-token",
        "refresh-token",
        "app-secret_key",
        "password_hash",
        "token_hash",
    ],
)
def test_sanitizer_sanitizes_field_variants_in_plain_and_quoted_text(field: str) -> None:
    """完整键名及可选分隔符在文本与序列化映射中均保持脱敏。"""
    assert Sanitizer.sanitize_text(f"{field}=private-value") == f"{field}=***"
    for quote in ('"', "'"):
        serialized = f"{{{quote}{field}{quote}: {quote}private-value{quote}, 'safe': 'visible'}}"
        sanitized = Sanitizer.sanitize_text(serialized)
        assert "private-value" not in sanitized
        assert f"{quote}{field}{quote}:" in sanitized
        assert "'safe': 'visible'" in sanitized


def test_sanitizer_sanitizes_required_audit_fields_and_complete_cookie_header() -> None:
    """验证码、身份号码及完整 Cookie 头均不进入输出。"""
    raw = (
        "verification_code=123456 sms_code=654321 id_card=110101199001011234\n"
        "验证码：456789 身份证号：110101199001011235\n"
        "Cookie: session=raw-session; csrf=raw-csrf"
    )

    sanitized = Sanitizer.sanitize_text(raw)

    assert "123456" not in sanitized
    assert "654321" not in sanitized
    assert "110101199001011234" not in sanitized
    assert "456789" not in sanitized
    assert "110101199001011235" not in sanitized
    assert "raw-session" not in sanitized
    assert "raw-csrf" not in sanitized


def test_sanitizer_preserves_outer_exception_after_sanitizing_inner_value() -> None:
    """清理底层异常敏感值后保留外层异常的诊断信息。"""
    try:
        try:
            raise ValueError({"access_token": "super-secret"})
        except ValueError as inner:
            raise RuntimeError("outer root cause") from inner
    except RuntimeError as outer:
        sanitized = Sanitizer.sanitize_text(
            "".join(traceback.format_exception(type(outer), outer, outer.__traceback__))
        )

    assert "super-secret" not in sanitized
    assert "outer root cause" in sanitized
    assert "RuntimeError" in sanitized


def test_sanitizer_preserves_outer_exception_after_unclosed_sensitive_quote() -> None:
    """未闭合引号的脱敏边界不会吞掉外层异常。"""
    raw_trace = (
        "ValueError: {'password': 'unterminated-secret\n\n"
        "The above exception was the direct cause of the following exception:\n\n"
        "RuntimeError: outer root cause"
    )

    sanitized = Sanitizer.sanitize_text(raw_trace)

    assert "unterminated-secret" not in sanitized
    assert "outer root cause" in sanitized
    assert "RuntimeError" in sanitized


def test_sanitizer_preserves_outer_exception_after_unclosed_sensitive_mapping() -> None:
    """未闭合映射的脱敏边界不会吞掉外层异常。"""
    raw_trace = (
        'ValueError: {"password": {"raw": "inner-secret"\n\n'
        "The above exception was the direct cause of the following exception:\n\n"
        "RuntimeError: outer root cause"
    )

    sanitized = Sanitizer.sanitize_text(raw_trace)

    assert "inner-secret" not in sanitized
    assert "outer root cause" in sanitized
    assert "RuntimeError" in sanitized


def test_sanitizer_preserves_exception_group_sibling_after_unclosed_sensitive_mapping() -> None:
    """异常组中不完整的敏感映射不会覆盖相邻异常。"""

    class MalformedSensitiveError(Exception):
        def __str__(self) -> str:
            """模拟含未闭合敏感映射的异常文本。"""
            return '{"password": {"raw": "inner-secret"'

    error_group = ExceptionGroup(
        "group failed",
        [MalformedSensitiveError(), RuntimeError("SIBLING-ROOT")],
    )
    raw_trace = "".join(traceback.format_exception(error_group))

    sanitized = Sanitizer.sanitize_text(raw_trace)

    assert "inner-secret" not in sanitized
    assert "SIBLING-ROOT" in sanitized
    assert "RuntimeError" in sanitized


def test_sanitizer_sanitizes_structured_log_values() -> None:
    """日志中的异常对象和嵌套数据都经过脱敏。"""
    sanitized = Sanitizer.sanitize_log_value(
        {
            "error": ValueError("password=super-secret"),
            "verification_code": "123456",
            "nested": {"safe": "access_token=raw-token"},
        }
    )

    assert sanitized == {
        "error": "password=***",
        "verification_code": "***",
        "nested": {"safe": "access_token=***"},
    }


def test_sanitizer_sanitizes_actual_captcha_fields_without_metric_false_positives() -> None:
    """实际验证码字段会脱敏，普通指标和近似字段名保持原值。"""
    sanitized = Sanitizer.sanitize_log_value(
        {
            "captcha_verification": "captcha-secret",
            "point_json": "point-secret",
            "ticket": "ticket-secret",
            "randstr": "rand-secret",
            "identity_no": "110101199001011234",
            "token_count": 3,
            "secretary": "Alice",
        }
    )

    assert sanitized == {
        "captcha_verification": "***",
        "point_json": "***",
        "ticket": "***",
        "randstr": "***",
        "identity_no": "***",
        "token_count": 3,
        "secretary": "Alice",
    }


def test_sanitizer_sanitizes_credential_aliases() -> None:
    """不同凭据字段别名在文本和映射中均会脱敏。"""
    sanitized = Sanitizer.sanitize_log_value(
        {
            "secret_key": "key-secret",
            "secret_id": "id-secret",
            "app_secret_key": "app-secret",
            "authorization_code": "authorization-secret",
            "authorization_header": "Basic header-secret",
        }
    )

    assert sanitized == {
        "secret_key": "***",
        "secret_id": "***",
        "app_secret_key": "***",
        "authorization_code": "***",
        "authorization_header": "***",
    }
    assert Sanitizer.sanitize_text("secret_key=key-secret") == "secret_key=***"
    assert (
        Sanitizer.sanitize_text("authorization_header=header-secret") == "authorization_header=***"
    )


def test_sanitizer_sanitizes_log_keys_cycles_and_unknown_objects() -> None:
    """日志键也会脱敏，递归结构和未知对象使用安全占位。"""

    class SecretObject:
        def __str__(self) -> str:
            """模拟不应直接暴露的未知对象文本。"""
            return "bare-secret-value"

    recursive: dict[str, object] = {}
    recursive["self"] = recursive

    sanitized = Sanitizer.sanitize_log_value(
        {
            "token=raw-key-secret": "safe",
            "recursive": recursive,
            "object": SecretObject(),
        }
    )

    assert sanitized == {
        "token=***": "***",
        "recursive": {"self": "<recursive>"},
        "object": "<SecretObject>",
    }


def test_trace_formatter_preserves_exception_chain_and_removes_credentials() -> None:
    """新诊断入口保留完整异常链，同时清理各层凭据。"""
    try:
        try:
            raise ValueError("password=private-inner")
        except ValueError as original:
            raise RuntimeError("outer failure") from original
    except RuntimeError as failure:
        result = "".join(ExceptionTraceFormatter.format(failure))
    assert "ValueError" in result
    assert "RuntimeError: outer failure" in result
    assert "password=***" in result
    assert "private-inner" not in result


def test_trace_formatter_falls_back_without_leaking_formatting_failure(monkeypatch) -> None:
    """堆栈格式化自身失败时只返回两类异常名称，不暴露二次错误详情。"""

    def broken_format(*args, **kwargs):
        """模拟标准库堆栈格式化故障。"""
        raise ValueError("private-format-detail")

    monkeypatch.setattr(traceback, "format_exception", broken_format)
    result = "".join(ExceptionTraceFormatter.format(RuntimeError("private-original")))
    assert "RuntimeError" in result
    assert "ValueError" in result
    assert "private" not in result


@pytest.mark.parametrize("signal", [KeyboardInterrupt(), SystemExit(3), CancelledError()])
def test_trace_formatter_does_not_swallow_control_signals(monkeypatch, signal) -> None:
    """诊断格式化过程中的中断、退出和取消仍向调用者传播。"""

    def interrupted_format(*args, **kwargs):
        """在诊断阶段触发指定控制异常。"""
        raise signal

    monkeypatch.setattr(traceback, "format_exception", interrupted_format)
    with pytest.raises(type(signal)) as captured:
        ExceptionTraceFormatter.format(RuntimeError("original"))
    assert captured.value is signal


def test_terminal_reporter_sanitizes_output_and_preserves_original_on_write_failure(
    monkeypatch, capsys
) -> None:
    """终端报告经过脱敏，终端不可写时只附注失败类型并保留主异常。"""
    original = RuntimeError("primary failure")
    failure = ValueError("password=private-terminal")
    TerminalErrorReporter.report("清理失败", failure, original)
    output = capsys.readouterr().err
    assert "password=***" in output
    assert "private-terminal" not in output

    class ClosedStream:
        def write(self, text) -> None:
            """模拟已关闭的终端流。"""
            raise OSError("private-stream-detail")

    monkeypatch.setattr(sys, "stderr", ClosedStream())
    TerminalErrorReporter.report("清理失败", failure, original)
    assert str(original) == "primary failure"
    assert any("OSError" in note for note in original.__notes__)
    assert "private-stream-detail" not in "".join(original.__notes__)
