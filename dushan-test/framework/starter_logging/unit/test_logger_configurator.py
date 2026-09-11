import json
from pathlib import Path

import pytest
from config_factory import ConfigFactory
from loguru import logger

from framework.common.enums.application_environment_enum import (
    ApplicationEnvironmentEnum,
)
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.context.log_context import LogContext
from framework.starter_logging.core.logger_configurator import LoggerConfigurator
from framework.starter_logging.starter.logging_starter import LoggingStarter

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_log_context() -> None:
    """每个测试前后清空当前任务的日志上下文。"""
    LogContext.clear()
    yield
    LogContext.clear()


def test_log_settings_reject_invalid_file_type() -> None:
    """未定义的日志文件类型不能进入配置。"""
    with pytest.raises(ValueError):
        ConfigFactory.build(LogSettings, "log", file_active_types={"audit"})


def test_log_settings_reject_invalid_level() -> None:
    """未定义的日志级别不能进入配置。"""
    with pytest.raises(ValueError):
        ConfigFactory.build(LogSettings, "log", console_level="verbose")


def test_configurator_redacts_message_and_injects_request_context(
    tmp_path: Path,
) -> None:
    """配置器清理凭据并补入请求、追踪和身份上下文。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None
    settings = ConfigFactory.build(
        LogSettings, "log", root_dir=str(tmp_path), enable_file_overall=False, console_level="INFO"
    )
    messages: list[str] = []
    request_token = LogContext.begin_request("request-1")
    trace_token = LogContext.bind_trace("trace-1", "span-1")
    LogContext.set_tenant(7)
    LogContext.set_principal(42, 142, "tenant")
    LogContext.set_client_ip("203.0.113.10")

    try:
        configurator.configure_logging(settings, app_env="test")
        handler_id = logger.add(
            messages.append,
            level="INFO",
            format=(
                "{message}|{extra[request_id]}|{extra[trace_id]}|{extra[span_id]}|{extra[tenant_id]}|"
                "{extra[account_id]}|{extra[membership_id]}|{extra[realm]}|{extra[client_ip]}"
            ),
        )

        logger.info("login token=abc123 Authorization: Bearer ey.secret")
    finally:
        LogContext.reset(trace_token)
        LogContext.reset(request_token)
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert len(messages) == 1
    assert "abc123" not in messages[0]
    assert "ey.secret" not in messages[0]
    assert messages[0].endswith("|request-1|trace-1|span-1|7|42|142|tenant|203.0.113.10\n")


def test_context_fields_publish_explicit_empty_principal_values() -> None:
    """空上下文仍包含格式器需要的全部字段。"""
    assert LoggerConfigurator._get_context_fields() == {
        "request_id": "-",
        "trace_id": "-",
        "span_id": "-",
        "tenant_id": "-",
        "account_id": "-",
        "membership_id": "-",
        "realm": "-",
        "client_ip": "-",
    }


def test_configurator_uses_protocol_neutral_client_ip_context() -> None:
    """客户端地址由日志上下文传递，不依赖 HTTP 请求。"""
    messages: list[str] = []
    token = LogContext.begin_request("client-ip-test")
    LogContext.set_client_ip("198.51.100.8")
    handler_id = logger.add(
        lambda message: messages.append(message.record["extra"]["client_ip"]),
        filter=lambda record: record["extra"].get("protocol_neutral_test") is True,
    )
    try:
        logger.patch(LoggerConfigurator._patch_record).bind(protocol_neutral_test=True).info(
            "ws event"
        )
    finally:
        logger.remove(handler_id)
        LogContext.reset(token)

    assert messages == ["198.51.100.8"]


def test_warning_file_sink_uses_minimum_level(tmp_path: Path) -> None:
    """警告文件也记录级别更高的错误日志。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"warning"},
        enqueue=False,
        compression=None,
    )

    try:
        configurator.configure_logging(settings, app_env="test")
        logger.warning("warn event")
        logger.error("error event")
    finally:
        configurator.remove_owned_handlers()

    warning_files = list(tmp_path.glob("*_warning.log"))
    assert len(warning_files) == 1
    warning_text = warning_files[0].read_text(encoding="utf-8")
    assert "warn event" in warning_text
    assert "error event" in warning_text


def test_configurator_redacts_exception_trace(tmp_path: Path) -> None:
    """异常堆栈保留诊断类型，同时清理敏感内容。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None
    settings = ConfigFactory.build(
        LogSettings, "log", root_dir=str(tmp_path), enable_file_overall=False, console_level="INFO"
    )
    messages: list[str] = []

    try:
        configurator.configure_logging(settings, app_env="test")
        handler_id = logger.add(messages.append, format="{message}{extra[exception_trace]}")
        try:
            raise ValueError({"access_token": "super-secret"})
        except ValueError:
            logger.exception("provider failed")
    finally:
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert len(messages) == 1
    assert "super-secret" not in messages[0]
    assert "access_token" in messages[0]
    assert "***" in messages[0]
    assert "ValueError" in messages[0]


def test_configurator_redacts_bound_exception_in_serialized_output() -> None:
    """绑定的异常对象在结构化输出中也要脱敏。"""
    messages: list[str] = []
    handler_id = logger.add(messages.append, serialize=True)
    try:
        error = ValueError("password=super-secret")
        logger.patch(LoggerConfigurator._patch_record).bind(error=error).opt(exception=error).error(
            "failed"
        )
    finally:
        logger.remove(handler_id)

    record = json.loads(messages[0])["record"]
    assert record["extra"]["error"] == "password=***"
    assert "super-secret" not in messages[0]


def test_configurator_redacts_sensitive_keyword_argument_already_formatted_into_message(
    tmp_path,
) -> None:
    """敏感关键字已被格式化进消息时仍会被清理。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None
    settings = ConfigFactory.build(
        LogSettings, "log", enable_file_overall=False, console_level="NONE"
    )
    messages: list[str] = []

    try:
        configurator.configure_logging(settings, app_env="test")
        handler_id = logger.add(messages.append, format="{message}|{extra[verification_code]}")
        logger.info("verification result={verification_code}", verification_code="654321")
    finally:
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert messages == ["verification result=***|***\n"]


def test_configurator_redacts_non_string_sensitive_arguments_from_message(tmp_path) -> None:
    """字节串和自定义对象形式的凭据不能绕过脱敏。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None

    class CredentialValue:
        def __str__(self) -> str:
            """返回用于验证脱敏的对象文本。"""
            return "object-credential-secret"

    settings = ConfigFactory.build(
        LogSettings, "log", enable_file_overall=False, console_level="NONE"
    )
    messages: list[str] = []

    try:
        configurator.configure_logging(settings, app_env="test")
        handler_id = logger.add(
            messages.append, format="{message}|{extra[token]}|{extra[credential]}"
        )
        logger.info(
            "bytes={} object={}",
            b"bytes-credential-secret",
            CredentialValue(),
            token=b"bytes-credential-secret",
            credential=CredentialValue(),
        )
    finally:
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert "bytes-credential-secret" not in messages[0]
    assert "object-credential-secret" not in messages[0]
    assert messages == ["***|***|***\n"]


def test_configurator_redacts_sensitive_object_custom_format_and_repr(tmp_path) -> None:
    """自定义格式化和 repr 不会泄露绑定的敏感对象。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None

    class CredentialValue:
        def __str__(self) -> str:
            """返回用于验证脱敏的对象文本。"""
            return "string-credential-secret"

        def __repr__(self) -> str:
            """返回用于验证脱敏的调试文本。"""
            return "repr-credential-secret"

        def __format__(self, _format_spec: str) -> str:
            """返回用于验证脱敏的自定义格式文本。"""
            return "format-credential-secret"

    settings = ConfigFactory.build(
        LogSettings, "log", enable_file_overall=False, console_level="NONE"
    )
    messages: list[str] = []
    credential = CredentialValue()

    try:
        configurator.configure_logging(settings, app_env="test")
        handler_id = logger.add(messages.append, format="{message}|{extra[credential]}")
        logger.info("default={} repr={!r}", credential, credential, credential=credential)
    finally:
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert messages == ["***|***\n"]


def test_managed_json_sink_redacts_values_added_by_later_patcher(
    tmp_path: Path,
) -> None:
    """受管 JSON 输出在后置补丁注入敏感信息后再次脱敏。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        enable_json_format=True,
        console_level="NONE",
        file_active_types=set(),
        enqueue=False,
        compression=None,
    )

    def inject_secret(record) -> None:
        """模拟后置补丁注入凭据。"""
        record["message"] = "post-patcher-secret"
        record["extra"]["password"] = "post-patcher-secret"

    try:
        configurator.configure_logging(settings, app_env="test")
        logger.patch(inject_secret).info("safe")
    finally:
        configurator.remove_owned_handlers()

    json_file = next(tmp_path.glob("*_structured_test.jsonl"))
    output = json_file.read_text(encoding="utf-8")
    assert "post-patcher-secret" not in output
    assert '"message": "***"' in output
    assert '"password": "***"' in output


def test_log_directory_creation_failure_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """日志目录创建失败时明确报错。"""
    configurator = LoggerConfigurator(base_dir=tmp_path)

    def fail_mkdir(*args, **kwargs) -> None:
        """模拟日志目录创建失败。"""
        raise PermissionError("no write permission")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(PermissionError, match="no write permission"):
        configurator._ensure_log_dir()


def test_disabled_file_output_does_not_create_directory(tmp_path: Path) -> None:
    """关闭文件日志后不创建日志目录。"""
    configurator = LoggerConfigurator(tmp_path)
    log_dir = tmp_path / "disabled" / "logs"
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(log_dir),
        enable_file_overall=False,
        enable_json_format=True,
        console_level="NONE",
    )

    try:
        configurator.configure_logging(settings, app_env="test")
    finally:
        configurator.remove_owned_handlers()

    assert not log_dir.exists()


def test_loadtest_mode_disables_text_and_json_files(tmp_path: Path) -> None:
    """压力测试模式同时禁用文本和 JSON 文件日志。"""
    configurator = LoggerConfigurator(tmp_path)
    log_dir = tmp_path / "loadtest" / "logs"
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(log_dir),
        enable_file_overall=True,
        enable_json_format=True,
        loadtest_mode=True,
        file_active_types={"info", "warning", "error"},
    )

    try:
        configurator.configure_logging(settings, app_env="test")
    finally:
        configurator.remove_owned_handlers()

    assert not log_dir.exists()


def test_json_file_sink_is_created_when_file_output_is_enabled(tmp_path: Path) -> None:
    """启用结构化文件日志后能够写出 JSON 行。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        enable_json_format=True,
        console_level="NONE",
        file_active_types=set(),
        enqueue=False,
        compression=None,
    )

    try:
        configurator.configure_logging(settings, app_env="test")
        logger.info("structured event")
    finally:
        configurator.remove_owned_handlers()

    json_files = list(tmp_path.glob("*_structured_test.jsonl"))
    assert len(json_files) == 1
    assert "structured event" in json_files[0].read_text(encoding="utf-8")


def test_failed_file_sink_keeps_stderr_fallback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """文件输出初始化失败时仍能在终端看到脱敏的错误原因。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"error"},
        enqueue=False,
        compression=None,
    )
    original_add = logger.add

    def fail_file_sink(sink, *args, **kwargs) -> int:
        """仅让文件输出安装失败，保留终端输出。"""
        if isinstance(sink, Path):
            raise OSError("file sink unavailable password=super-secret")
        return original_add(sink, *args, **kwargs)

    monkeypatch.setattr(logger, "add", fail_file_sink)
    try:
        with pytest.raises(OSError, match="file sink unavailable"):
            LoggingStarter(configurator=configurator).initialize(
                app_env="test", log_settings=settings
            )
    finally:
        configurator.remove_owned_handlers()

    error_output = capsys.readouterr().err
    assert "LoggingStarter" in error_output
    assert "file sink unavailable" in error_output
    assert "Traceback (most recent call last)" in error_output
    assert "super-secret" not in error_output
    assert "password=***" in error_output


def test_log_directory_preflight_keeps_existing_handler(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """目录预检失败不会移除其他调用者的日志输出。"""
    configurator = LoggerConfigurator(tmp_path)
    handler_id = None
    messages: list[str] = []
    handler_id = logger.add(messages.append, format="{message}")
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"error"},
    )

    def fail_mkdir(*args, **kwargs) -> None:
        """模拟日志目录创建失败。"""
        raise PermissionError("no write permission")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    try:
        with pytest.raises(PermissionError, match="no write permission"):
            configurator.configure_logging(settings, app_env="prod")
        logger.error("preflight failure remains visible")
    finally:
        if handler_id is not None:
            logger.remove(handler_id)
        configurator.remove_owned_handlers()

    assert messages == ["preflight failure remains visible\n"]


def test_resolve_env_uses_application_environment_enum() -> None:
    """环境名称忽略大小写并拒绝未定义值。"""
    assert LoggerConfigurator._resolve_env("DEV") == ApplicationEnvironmentEnum.DEVELOPMENT
    with pytest.raises(ValueError):
        LoggerConfigurator._resolve_env("local")


def test_directory_preflight_failure_uses_sanitized_fallback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """目录预检失败的终端提示和堆栈均不暴露凭据。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path / "logs"),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"error"},
    )

    def fail_mkdir(*args, **kwargs) -> None:
        """模拟日志目录创建失败。"""
        raise PermissionError("password=preflight-secret")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    try:
        with pytest.raises(PermissionError, match="preflight-secret"):
            LoggingStarter(configurator=configurator).initialize(
                app_env="prod", log_settings=settings
            )
    finally:
        configurator.remove_owned_handlers()

    error_output = capsys.readouterr().err
    assert "preflight-secret" not in error_output
    assert "password=***" in error_output
    assert "Traceback (most recent call last)" in error_output


def test_logging_starter_retries_cleanly_after_sink_installation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """首次文件输出安装失败后可以重新初始化并记录日志。"""
    configurator = LoggerConfigurator(tmp_path)
    settings = ConfigFactory.build(
        LogSettings,
        "log",
        root_dir=str(tmp_path),
        enable_file_overall=True,
        console_level="NONE",
        file_active_types={"error"},
        enqueue=False,
        compression=None,
    )
    original_add = logger.add
    failed_once = False

    def fail_first_file_sink(sink, *args, **kwargs) -> int:
        """仅第一次安装文件输出时失败。"""
        nonlocal failed_once
        if isinstance(sink, Path) and not failed_once:
            failed_once = True
            raise OSError("first file sink failed")
        return original_add(sink, *args, **kwargs)

    monkeypatch.setattr(logger, "add", fail_first_file_sink)
    starter = LoggingStarter(configurator=configurator)
    try:
        with pytest.raises(OSError, match="first file sink failed"):
            starter.initialize(app_env="test", log_settings=settings)
        starter.initialize(app_env="test", log_settings=settings)
        logger.error("retry event")
    finally:
        configurator.remove_owned_handlers()

    assert starter.initialized is True
    error_file = next(tmp_path.glob("*_error.log"))
    assert "retry event" in error_file.read_text(encoding="utf-8")
