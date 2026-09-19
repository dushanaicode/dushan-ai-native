import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from threading import RLock
from urllib.parse import urlsplit
from uuid import uuid4

from loguru import logger
from opentelemetry import context, trace
from opentelemetry.context import Context
from opentelemetry.trace import SpanKind

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_di.exception.di_exception import DiException
from framework.starter_logging.context.log_context import LogContext
from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.monitor_attribute_policy import MonitorAttributePolicy
from framework.starter_monitor.core.monitor_diagnostics import MonitorDiagnostics
from framework.starter_monitor.core.monitor_span import MonitorSpan
from framework.starter_monitor.core.sdk_log_guard import SdkLogGuard
from framework.starter_monitor.core.trace_binding import TraceBinding
from framework.starter_monitor.core.trace_propagation import TracePropagation
from framework.starter_monitor.definitions.constants.monitor_error_codes import MonitorErrorCodes
from framework.starter_monitor.exception.monitor_exception import MonitorException


@framework(scope=ComponentScopeEnum.SINGLETON)
class MonitorService:
    """应用独占的追踪入口，不发布进程全局Provider或传播器。

    受管代码可Inject本服务；非受管入口使用get_bean或显式bind。
    span只接受明确属性，extract/inject处理标准传播。启用时open接管传入Exporter的生命周期，
    close由宿主在业务排空后调用；直接关闭时会结束尚存的观测Span，不取消业务任务。
    """

    def __init__(self, settings: MonitorSettings):
        self.settings = settings
        self.diagnostics = MonitorDiagnostics()
        self.policy = MonitorAttributePolicy(settings)
        self.propagation = TracePropagation(settings, self.diagnostics)
        self.database = None
        self._provider = None
        self._tracer = None
        self._exporter = None
        self._processor = None
        self._pool = None
        self._guard_owned = False
        self._lock = RLock()
        self._spans: set[MonitorSpan] = set()
        self._state = "new"
        self._close_task = None
        self._flush_task = None

    @classmethod
    def current(cls):
        binding = TraceBinding.current.get()
        try:
            application = ApplicationContext.current()
        except DiException:
            return binding.owner if binding is not None and binding.active else None
        try:
            return application.get_bean(cls)
        except DiException:
            return None

    async def open(self, *, diagnostic_logger, exporter=None):
        if self._state != "new":
            raise MonitorException(MonitorErrorCodes.INIT_FAILED)
        self.diagnostics.logger = diagnostic_logger
        if not self.settings.enabled:
            self._state = "disabled"
            logger.info("【MonitorStarter 】链路追踪未启用")
            return
        logger.info("【MonitorStarter 】开始初始化链路追踪资源")
        self._state = "starting"
        try:
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import SpanLimits, TracerProvider

            from framework.starter_monitor.core.bounded_span_exporter import BoundedSpanExporter
            from framework.starter_monitor.core.monitor_span_processor import MonitorSpanProcessor

            settings = self.settings
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="monitor-lifecycle")
            self._provider = TracerProvider(
                resource=Resource(
                    {
                        "service.name": settings.service_name,
                        "service.version": settings.service_version,
                        "service.instance.id": settings.instance_id or uuid4().hex,
                    }
                ),
                sampler=self._sampler(),
                span_limits=SpanLimits(
                    max_attributes=settings.max_attributes,
                    max_events=settings.max_events,
                    max_links=0,
                    max_attribute_length=settings.max_attribute_length,
                    max_event_attributes=settings.max_attributes,
                    max_link_attributes=0,
                ),
                shutdown_on_exit=False,
            )
            SdkLogGuard.acquire()
            logger.info("【MonitorStarter 】TracerProvider 与采样策略已装配")
            self._guard_owned = True
            with SdkLogGuard.quiet():
                self._exporter = exporter if exporter is not None else self._create_exporter()
            if self._exporter is not None:
                bounded = BoundedSpanExporter(
                    self._exporter, settings.export_timeout_seconds, self.diagnostics
                )
                self._processor = MonitorSpanProcessor(bounded, settings)
                self._provider.add_span_processor(self._processor)
            self._tracer = self._provider.get_tracer("dushan.monitor", settings.service_version)
            logger.info(
                "【MonitorStarter 】导出器已装配：{}",
                type(self._exporter).__qualname__ if self._exporter is not None else "未启用",
            )
            logger.debug(
                "【MonitorStarter 】服务={} version={} sampler={} sample_ratio={}",
                settings.service_name,
                settings.service_version,
                settings.sampler,
                settings.sample_ratio,
            )
            self._state = "ready"
            logger.info("【MonitorStarter 】初始化完成：{}", settings.service_name)
        except BaseException as error:
            self._state = "failed"
            if isinstance(error, Exception):
                raise MonitorException(MonitorErrorCodes.INIT_FAILED, cause=error) from error
            raise

    def _sampler(self):
        from opentelemetry.sdk.trace.sampling import (
            ALWAYS_OFF,
            ALWAYS_ON,
            ParentBased,
            TraceIdRatioBased,
        )

        name = self.settings.sampler
        root = {
            "always_on": ALWAYS_ON,
            "always_off": ALWAYS_OFF,
            "traceidratio": TraceIdRatioBased(self.settings.sample_ratio),
        }[name.removeprefix("parentbased_")]
        return ParentBased(root) if name.startswith("parentbased_") else root

    def _create_exporter(self):
        if self.settings.exporter == "none":
            return None
        from grpc import Compression, StatusCode, ssl_channel_credentials
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.metrics import NoOpMeterProvider

        insecure = urlsplit(self.settings.endpoint).scheme == "http"
        # 非空metadata防止SDK把应用的空配置替换成进程级OTEL_*头。
        headers = {"x-dushan-monitor": "1"}
        headers.update(
            {key: value.get_secret_value() for key, value in self.settings.export_headers.items()}
        )
        return OTLPSpanExporter(
            endpoint=self.settings.endpoint,
            insecure=insecure,
            credentials=None if insecure else ssl_channel_credentials(),
            headers=headers,
            timeout=self.settings.export_timeout_seconds,
            compression=Compression.NoCompression,
            channel_options=(
                ("grpc.max_receive_message_length", 65536),
                ("grpc.max_send_message_length", 8388608),
            ),
            retryable_error_codes=(StatusCode.UNAVAILABLE, StatusCode.RESOURCE_EXHAUSTED),
            meter_provider=NoOpMeterProvider(),
        )

    def _finished(self, span):
        with self._lock:
            self._spans.discard(span)

    def _observe(self, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException:
            self.diagnostics.increment("observation_failures", warn=True)
            return None

    @contextmanager
    def bind(self, parent: Context | None = None):
        """独立入口显式绑定应用，退出恢复调用方上下文；不隐式建立业务Span。"""
        token = context.attach(
            Context() if parent is None else self.propagation.clean_context(parent)
        )
        frame = TraceBinding(self, None)
        binding = TraceBinding.current.set(frame)
        log = LogContext.bind_trace(None, None)
        try:
            yield
        finally:
            frame.active = False
            LogContext.reset(log)
            TraceBinding.current.reset(binding)
            context.detach(token)

    @contextmanager
    def span(
        self,
        name: str,
        attributes=None,
        *,
        kind=SpanKind.INTERNAL,
        parent: Context | None = None,
        start_time=None,
    ):
        binding = TraceBinding.current.get()
        inherited = binding is not None and binding.active and binding.owner is self
        parent = parent if parent is not None else context.get_current() if inherited else Context()
        stack = ExitStack()
        frame = None
        span = trace.INVALID_SPAN
        try:
            if self._state != "ready" or SdkLogGuard.suppressed():
                parent = Context()
            else:
                parent = self.propagation.clean_context(parent)
            token = context.attach(parent)
            stack.callback(context.detach, token)
            with self._lock:
                if self._state == "ready" and not SdkLogGuard.suppressed():
                    raw = self._tracer.start_span(
                        self.policy.text(name),
                        context=parent,
                        kind=kind,
                        attributes=self.policy.attributes(attributes),
                        start_time=start_time,
                    )
                    span = MonitorSpan(raw, self.policy, self.diagnostics, self._finished)
                    self._spans.add(span)
                    self.diagnostics.increment("started_spans")
            stack.enter_context(
                trace.use_span(
                    span, end_on_exit=False, record_exception=False, set_status_on_exception=False
                )
            )
            frame = TraceBinding(self, span)
            current = TraceBinding.current.set(frame)
            stack.callback(TraceBinding.current.reset, current)
            ids = span.get_span_context()
            log = LogContext.bind_trace(
                format(ids.trace_id, "032x") if ids.is_valid else None,
                format(ids.span_id, "016x") if ids.is_valid else None,
            )
            stack.callback(LogContext.reset, log)
        except BaseException:
            self.diagnostics.increment("span_start_failures", warn=True)
            self._observe(stack.close)
            self._observe(span.end)
            span = trace.INVALID_SPAN
        try:
            yield span
        except BaseException as error:
            if isinstance(error, (asyncio.CancelledError, GeneratorExit)):
                self._observe(span.add_event, "cancelled", {"operation.cancelled": True})
            else:
                self._observe(span.record_exception, error, escaped=True)
            raise
        finally:
            if frame is not None:
                frame.active = False
            self._observe(span.end)
            self._observe(stack.close)

    def extract(self, headers) -> Context:
        if not self.settings.enabled:
            return Context()
        with SdkLogGuard.quiet():
            parsed = self._observe(self.propagation.extract, headers)
        return Context() if parsed is None else parsed

    def inject(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        binding = TraceBinding.current.get()
        parent = (
            context.get_current()
            if binding is not None and binding.active and binding.owner is self
            else Context()
        )
        with SdkLogGuard.quiet():
            result = self._observe(self.propagation.inject, parent, headers)
        return dict(headers or {}) if result is None else result

    def on_error(self, error: BaseException) -> None:
        binding = TraceBinding.current.get()
        if (
            binding is not None
            and binding.active
            and binding.owner is self
            and binding.span is not None
        ):
            self._observe(binding.span.record_exception, error)

    async def flush(self) -> bool:
        if self._state != "ready" or self._processor is None:
            return self._state in {"ready", "disabled"}
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush(), name="monitor-flush")
        return await asyncio.shield(self._flush_task)

    async def _flush(self):
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                self._pool,
                self._processor.force_flush,
                int(self.settings.flush_timeout_seconds * 1000),
            )
            if not result:
                self.diagnostics.increment("flush_failures", warn=True)
            return result
        except BaseException:
            self.diagnostics.increment("flush_failures", warn=True)
            return False

    async def close(self):
        if self._close_task is None or self._state == "close_failed":
            with self._lock:
                self._state = "closing"
            if self._processor is not None:
                self._processor.begin_shutdown()
            if self._provider is not None and self._pool is None:
                self._pool = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="monitor-lifecycle"
                )
            if self._exporter is not None and not self._guard_owned:
                SdkLogGuard.acquire()
                self._guard_owned = True
            self._close_task = asyncio.create_task(self._close(), name="monitor-close")
        await asyncio.shield(self._close_task)

    async def _close(self):
        errors = []
        try:
            with self._lock:
                spans = tuple(self._spans)
            for span in spans:
                span.end()
            if self._flush_task is not None:
                await self._flush_task
            if self._provider is not None:
                await asyncio.get_running_loop().run_in_executor(
                    self._pool, self._provider.shutdown
                )
            if self._processor is not None:
                await asyncio.get_running_loop().run_in_executor(
                    self._pool, self._processor.exporter.shutdown
                )
            elif self._exporter is not None:
                await asyncio.get_running_loop().run_in_executor(
                    self._pool, self._exporter.shutdown
                )
        except BaseException as error:
            errors.append(error)
            self.diagnostics.increment("shutdown_failures", warn=True)
        finally:
            if self._pool is not None:
                self._pool.shutdown(wait=True)
                self._pool = None
            if self._guard_owned:
                SdkLogGuard.release()
                self._guard_owned = False
            self._tracer = None
            self.database = None
            self._state = "closed" if not errors else "close_failed"
        if errors:
            raise MonitorException(MonitorErrorCodes.SHUTDOWN_FAILED, cause=errors[0]) from errors[
                0
            ]

    def get_statistics(self):
        return {
            "state": self._state,
            "active_spans": len(self._spans),
            "pending_spans": 0 if self._processor is None else self._processor.exporter.pending,
            **self.diagnostics.snapshot(),
        }
