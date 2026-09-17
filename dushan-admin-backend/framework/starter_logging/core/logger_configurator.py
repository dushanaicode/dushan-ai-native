import sys
import traceback
from pathlib import Path
from threading import RLock
from typing import ClassVar
from uuid import uuid4

from loguru import logger
from opentelemetry import trace

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum
from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.security.sanitizer import Sanitizer
from framework.starter_logging.config.logger_options import LoggerOptions
from framework.starter_logging.context.log_context import LogContext
from framework.starter_logging.enums.log_file_type_enum import LogFileTypeEnum


class LoggerConfigurator:
    """配置控制台、分级文件和结构化日志，并管理本实例创建的输出。

    用 configure_logging 安装日志输出，关闭时先 disable_managed_sinks，
    排空队列后调用 remove_owned_handlers；sink_ids 可用于检查资源是否已释放。
    logger.bind(logging_owner=owner_id) 的日志只进入对应实例；未绑定的进程日志
    交给最早启动且仍活动的实例，避免多应用重复输出。不要复用活动实例的 owner_id。
    全局 patcher 补齐上下文并脱敏，每个受管输出在写入前再次清理。
    """

    CONTEXT_EMPTY = "-"
    _active_configurators: ClassVar[list["LoggerConfigurator"]] = []
    _ownership_lock: ClassVar[RLock] = RLock()
    _default_sink_removed: ClassVar[bool] = False

    # 标准日志格式
    COMMON_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {process.id}:{thread.id} | "
        "{extra[context_text]}"
        "{message} - {name}:{function}:{line}{extra[exception_trace]}"
    )

    # 错误日志格式 (保留换行符特性)
    ERROR_FORMAT = COMMON_FORMAT + "\n"

    STARTUP_FALLBACK_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}{extra[exception_trace]}"
    )

    # 控制台彩色格式
    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "{extra[context_text]}"
        "<level>{message}</level> - "
        "<cyan>{name}:{function}:{line}</cyan>{extra[exception_trace]}"
    )

    def __init__(self, base_dir: Path, *, owner_id: str | None = None):
        """保存日志目录与实例标识，尚不创建目录或日志输出。"""
        self._base_dir = base_dir.resolve()
        self._log_dir = self._base_dir
        self.owner_id = owner_id if owner_id is not None else uuid4().hex
        self._sink_ids: set[int] = set()
        self._managed_sinks_active = False

    @property
    def sink_ids(self) -> tuple[int, ...]:
        """返回当前实例持有的日志输出编号快照。"""
        with self._ownership_lock:
            return tuple(sorted(self._sink_ids))

    def _activate(self) -> None:
        """登记本实例，使未绑定日志按启动顺序选择唯一输出实例。"""
        with self._ownership_lock:
            if any(
                item is not self and item.owner_id == self.owner_id
                for item in self._active_configurators
            ):
                raise ValueError("活动日志实例不能使用相同 owner_id")
            if self not in self._active_configurators:
                self._active_configurators.append(self)
            self._managed_sinks_active = True

    @classmethod
    def _remove_default_sink(cls) -> None:
        """首次接管时移除 Loguru 默认输出，保留调用方添加的输出。"""
        with cls._ownership_lock:
            if LoggerConfigurator._default_sink_removed:
                return
            try:
                logger.remove(0)
            except ValueError:
                pass
            LoggerConfigurator._default_sink_removed = True

    def _track_sink(self, sink_id: int) -> int:
        """记录新日志输出的归属并返回编号。"""
        with self._ownership_lock:
            self._sink_ids.add(sink_id)
        return sink_id

    def _remove_sink(self, sink_id: int) -> None:
        """移除一个自身持有的日志输出，失败时保留编号以便核查。"""
        with self._ownership_lock:
            if sink_id not in self._sink_ids:
                return
        logger.remove(sink_id)
        with self._ownership_lock:
            self._sink_ids.discard(sink_id)

    def remove_owned_handlers(self) -> None:
        """停止接收新日志并移除本实例的输出，保留其他实例和调用方的输出。"""
        self.disable_managed_sinks()
        self._reset_handlers()

    def _add_file_sink(
        self,
        log_path: Path,
        level: LogLevelEnum,
        file_type: LogFileTypeEnum,
        retention: str,
        config: LoggerOptions,
    ) -> None:
        """按最低级别添加文本文件输出，并应用轮转、保留和压缩配置。"""
        if level == LogLevelEnum.NONE:
            return

        filename = f"{{time:YYYY-MM-DD}}_{file_type.code}.log"

        self._track_sink(
            logger.add(
                sink=log_path / filename,
                level=level.code,
                rotation=config.rotation_size,
                retention=retention,
                encoding="utf-8",
                enqueue=config.enqueue,
                compression=config.compression,
                format=self.ERROR_FORMAT
                if file_type == LogFileTypeEnum.ERROR
                else self.COMMON_FORMAT,
                filter=self._sanitize_record_filter,
                catch=True,
                backtrace=True,
                diagnose=False,
            )
        )

    def configure_logging(self, log_config: LoggerOptions, app_env: str) -> None:
        """安装本实例的日志输出，目录预检失败时保留已有输出和安全报告出口。"""
        env = self._resolve_env(app_env)
        self._log_dir = self._resolve_log_dir(log_config)
        has_file_output = self._has_file_output(log_config)
        self._configure_patcher()
        self._activate()
        if has_file_output:
            preflight_handler_id = self._add_startup_fallback_sink()
            self._ensure_log_dir()
            self._remove_sink(preflight_handler_id)

        self._remove_default_sink()
        self._reset_handlers()
        fallback_handler_id = self._add_startup_fallback_sink()
        self._add_console_sink(log_config, env)
        if has_file_output:
            self._add_active_file_sinks(log_config)
            self._add_json_sink(log_config, env)
        self._log_initialized(log_config, env)
        self._remove_sink(fallback_handler_id)

    @staticmethod
    def _resolve_env(app_env: str) -> ApplicationEnvironmentEnum:
        """按 Native 环境枚举解析应用环境。"""
        return ApplicationEnvironmentEnum(app_env.lower())

    def _resolve_log_dir(self, log_config: LoggerOptions) -> Path:
        """按配置目录解析日志路径，绝对路径由 Path 原样保留。"""
        return self._base_dir / log_config.root_dir

    def _reset_handlers(self) -> None:
        """逐一移除本实例的日志输出，某个输出失败后仍尝试清理其余输出。"""
        first_error: BaseException | None = None
        for sink_id in self.sink_ids:
            try:
                self._remove_sink(sink_id)
            except BaseException as error:
                if first_error is None:
                    first_error = error
                else:
                    first_error.add_note(f"另一个日志输出移除失败：{type(error).__name__}")
        if first_error is not None:
            raise first_error

    def _add_startup_fallback_sink(self) -> int:
        """保留同步 stderr sink，确保正式 sink 安装失败时仍能报告错误。"""
        return self._track_sink(
            logger.add(
                sink=sys.stderr,
                level=LogLevelEnum.ERROR.code,
                format=self.STARTUP_FALLBACK_FORMAT,
                filter=self._sanitize_record_filter,
                colorize=False,
                enqueue=False,
                catch=True,
                backtrace=False,
                diagnose=False,
            )
        )

    @classmethod
    def _configure_patcher(cls) -> None:
        """安装各实例共用的上下文补齐和脱敏函数。"""
        logger.configure(patcher=cls._patch_record)

    @classmethod
    def _patch_record(cls, record) -> None:
        """清理消息和异常链，补齐上下文并清理扩展字段。"""
        record["message"] = Sanitizer.sanitize_log_message(record["message"], record["extra"])
        exception_trace = cls._sanitize_exception(record)
        if exception_trace:
            record["extra"]["exception_trace"] = exception_trace
        else:
            record["extra"].setdefault("exception_trace", "")
        for key, value in cls._get_context_fields().items():
            record["extra"].setdefault(key, value)
        record["extra"] = Sanitizer.sanitize_log_value(record["extra"])
        context = " ".join(
            f"{label}={record['extra'][key]}"
            for key, label in (
                ("request_id", "request"),
                ("trace_id", "trace"),
                ("span_id", "span"),
                ("tenant_id", "tenant"),
                ("account_id", "account"),
                ("membership_id", "membership"),
                ("realm", "realm"),
                ("client_ip", "ip"),
            )
            if record["extra"][key] not in (None, "", cls.CONTEXT_EMPTY)
        )
        record["extra"]["context_text"] = context + " | " if context else ""

    def _sanitize_record_filter(self, record) -> bool:
        """在受管 sink 格式化前执行最终清理，阻断后置 patcher 旁路。"""
        with self._ownership_lock:
            if not self._managed_sinks_active:
                return False
            owner_id = record["extra"].get("logging_owner")
            if owner_id is not None:
                if owner_id != self.owner_id:
                    return False
            elif not self._active_configurators or self._active_configurators[0] is not self:
                return False
        self._patch_record(record)
        return True

    def disable_managed_sinks(self) -> None:
        """停止本实例接收新日志，并将未绑定日志交给下一个活动实例。"""
        with self._ownership_lock:
            self._managed_sinks_active = False
            if self in self._active_configurators:
                self._active_configurators.remove(self)

    @staticmethod
    def _sanitize_exception(record) -> str:
        """用脱敏异常链替换原始异常对象，避免日志系统再次输出未清理的堆栈。"""
        exception = record["exception"]
        if exception is None:
            return ""
        record["exception"] = None
        try:
            safe = SafeExceptionDiagnostics.snapshot(exception.value)
            formatted = "".join(
                traceback.format_exception(
                    exception.type if safe is exception.value else type(safe),
                    safe,
                    exception.traceback if safe is exception.value else safe.__traceback__,
                )
            )
        except Exception:
            formatted = f"{getattr(exception.type, '__name__', 'Exception')}：堆栈格式化失败"
        formatted = Sanitizer.sanitize_text(formatted)
        return f"\n{formatted.rstrip()}"

    @classmethod
    def _get_context_fields(cls) -> dict[str, str]:
        """读取本次日志的请求、追踪和身份字段，缺失值使用短横线。"""
        context = LogContext.current()
        trace_id, span_id = cls._get_trace_fields(context)
        return {
            "request_id": cls._context_value(context.request_id),
            "trace_id": cls._context_value(trace_id),
            "span_id": cls._context_value(span_id),
            "tenant_id": cls._context_value(context.tenant_id),
            "account_id": cls._context_value(context.account_id),
            "membership_id": cls._context_value(context.membership_id),
            "realm": cls._context_value(context.realm),
            "client_ip": cls._context_value(context.client_ip),
        }

    @staticmethod
    def _get_trace_fields(context: LogContext) -> tuple[str | None, str | None]:
        """优先读取有效 OpenTelemetry Span，否则保留显式日志上下文。"""
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            return format(span_context.trace_id, "032x"), format(span_context.span_id, "016x")
        return context.trace_id, context.span_id

    @classmethod
    def _context_value(cls, value: object | None) -> str:
        """将上下文字段转换为日志文本，None 使用缺失标记。"""
        if value is None:
            return cls.CONTEXT_EMPTY
        return str(value)

    def _ensure_log_dir(self) -> None:
        """创建日志目录，权限或路径错误直接交给启动流程处理。"""
        self._log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _has_file_output(log_config: LoggerOptions) -> bool:
        """判断是否存在任一最终生效的文件 sink。"""
        if not log_config.get_effective_file_enabled():
            return False
        if log_config.enable_json_format:
            return True
        active_levels = {
            LogFileTypeEnum.INFO: log_config.file_level_info,
            LogFileTypeEnum.WARNING: log_config.file_level_warning,
            LogFileTypeEnum.ERROR: log_config.file_level_error,
        }
        return any(
            file_type in log_config.file_active_types and level != LogLevelEnum.NONE
            for file_type, level in active_levels.items()
        )

    def _add_console_sink(
        self,
        log_config: LoggerOptions,
        env: ApplicationEnvironmentEnum,
    ) -> None:
        """添加控制台输出，开发环境使用颜色和同步写入。"""
        console_level = log_config.get_effective_console_level()
        if console_level == LogLevelEnum.NONE:
            return
        self._track_sink(
            logger.add(
                sink=sys.stdout,
                level=console_level.code,
                format=self.CONSOLE_FORMAT,
                filter=self._sanitize_record_filter,
                colorize=(env == ApplicationEnvironmentEnum.DEVELOPMENT),
                enqueue=(env != ApplicationEnvironmentEnum.DEVELOPMENT and log_config.enqueue),
                catch=True,
                backtrace=False,
                diagnose=False,
            )
        )

    def _add_active_file_sinks(self, log_config: LoggerOptions) -> None:
        """按配置添加信息、警告和错误文本文件输出。"""
        active_types = log_config.file_active_types
        if LogFileTypeEnum.INFO in active_types:
            self._add_file_sink(
                self._log_dir,
                log_config.file_level_info,
                LogFileTypeEnum.INFO,
                log_config.retention_info,
                log_config,
            )
        if LogFileTypeEnum.WARNING in active_types:
            self._add_file_sink(
                self._log_dir,
                log_config.file_level_warning,
                LogFileTypeEnum.WARNING,
                log_config.retention_warn,
                log_config,
            )
        if LogFileTypeEnum.ERROR in active_types:
            self._add_file_sink(
                self._log_dir,
                log_config.file_level_error,
                LogFileTypeEnum.ERROR,
                log_config.retention_error,
                log_config,
            )

    def _add_json_sink(
        self,
        log_config: LoggerOptions,
        env: ApplicationEnvironmentEnum,
    ) -> None:
        """添加 INFO 及以上级别的 JSONL 输出。"""
        if not log_config.enable_json_format:
            return
        json_filename = f"{{time:YYYY-MM-DD}}_structured_{env.value}.jsonl"
        self._track_sink(
            logger.add(
                sink=self._log_dir / json_filename,
                level=LogLevelEnum.INFO.code,
                rotation=log_config.rotation_size,
                retention=log_config.retention_info,
                encoding="utf-8",
                serialize=True,
                filter=self._sanitize_record_filter,
                enqueue=log_config.enqueue,
                compression=log_config.compression,
                backtrace=False,
                diagnose=False,
            )
        )

    def _log_initialized(
        self,
        log_config: LoggerOptions,
        env: ApplicationEnvironmentEnum,
    ) -> None:
        """向本实例的输出记录初始化结果或压测模式提醒。"""
        owned_logger = logger.bind(logging_owner=self.owner_id)
        if log_config.loadtest_mode:
            owned_logger.warning(
                "【LoggingStarter 】压测模式已开启：文件日志已关闭，控制台级别=WARNING，目录：{}",
                self._log_dir,
            )
        else:
            owned_logger.debug(
                "【LoggingStarter 】日志配置完成，目录：{}，环境：{}", self._log_dir, env.value
            )
