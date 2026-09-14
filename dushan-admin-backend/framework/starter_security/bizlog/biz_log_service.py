import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from jinja2 import TemplateError
from loguru import logger

from framework.common.security.request_identity import RequestIdentity
from framework.common.security.sanitizer import Sanitizer
from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_logging.context.log_context import LogContext
from framework.starter_security.bizlog.diff_renderer import DiffRenderer
from framework.starter_security.bizlog.expression.expression_utils import ExpressionUtils
from framework.starter_security.bizlog.log_record_context import LogRecordContext
from framework.starter_security.bizlog.log_record_entry import LogRecordEntry
from framework.starter_security.bizlog.log_record_operation import LogRecordOperation
from framework.starter_security.bizlog.log_record_provider import LogRecordProvider
from framework.starter_security.bizlog.log_record_reservation import LogRecordReservation
from framework.starter_security.bizlog.log_record_spec import LogRecordSpec
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.exception.security_exception import SecurityException


@framework(scope=ComponentScopeEnum.SINGLETON)
@conditional(lambda config: config.get_config(SecuritySettings).bizlog_enabled)
class BizLogService:
    """当前应用的业务审计；只冻结安全投影，不替提供者管理数据库事务。

    预留失败发生在业务前；业务后记录失败计数并独立报告，保持真实返回值、
    业务异常或取消。提供者可用既有事务/outbox 实现可恢复的持久交付。
    """

    def __init__(
        self,
        settings: SecuritySettings,
        provider: LogRecordProvider,
        security: SecurityContext,
        context: LogRecordContext,
        expression: ExpressionUtils,
    ):
        self.settings, self.provider = settings, provider
        self.security, self.context, self.expression = security, context, expression
        self._writing: ContextVar[bool] = ContextVar(f"bizlog_writing_{id(self)}", default=False)
        self._closed = False
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self.written = 0
        self.failed = 0

    async def _write(self, callback):
        token = self._writing.set(True)
        try:
            async with asyncio.timeout(self.settings.provider_timeout_seconds):
                return await callback()
        finally:
            self._writing.reset(token)

    async def invoke(self, spec: LogRecordSpec, callback, captured: dict):
        if self._closed:
            raise SecurityException("closed")
        if self._writing.get():
            raise RuntimeError("业务日志提供者不能递归记录自身")
        principal = self.security.require()
        operation = LogRecordOperation(
            uuid4().hex,
            spec.type,
            spec.sub_type,
            datetime.now(timezone.utc),
            RequestIdentity(principal_id=principal.account_id, tenant_id=principal.tenant_id),
            principal.realm,
            principal.authority_tenant_id,
            principal.membership_id,
            LogContext.current().trace_id,
            self.security.request_audit(),
        )
        self._active += 1
        self._idle.clear()
        try:
            with self.context.scope():
                for name, value in captured.items():
                    self.context.put(name, value)
                reservation = None

                async def reserve():
                    nonlocal reservation
                    reservation = await self._write(lambda: self.provider.reserve(operation))

                try:
                    await AsyncioUtils.run_cancellation_shielded(reserve())
                except asyncio.CancelledError:
                    if isinstance(reservation, LogRecordReservation):
                        await AsyncioUtils.run_cancellation_shielded(
                            self._cancel_reservation(reservation),
                            propagate_cancellation=False,
                        )
                    raise
                except Exception as error:
                    self._failure(error)
                    raise SecurityException("unavailable", cause=error) from error
                if (
                    not isinstance(reservation, LogRecordReservation)
                    or reservation.event_id != operation.event_id
                ):
                    raise SecurityException("configuration")
                heartbeat = (
                    self.security.application.tasks.create_task(
                        self._renew,
                        reservation,
                        name="bizlog-renew",
                        continuation=True,
                    )
                    if reservation.persistent
                    else None
                )
                started = perf_counter()
                business_error = None
                try:
                    try:
                        result = await callback()
                    except BaseException as error:
                        business_error = error
                        raise
                    finally:
                        duration = (perf_counter() - started) * 1000
                        await AsyncioUtils.run_cancellation_shielded(
                            self._finalize(spec, operation, reservation, business_error, duration),
                            propagate_cancellation=business_error is None,
                        )
                    return result
                finally:
                    if heartbeat is not None:
                        heartbeat.cancel()
                        await AsyncioUtils.run_cancellation_shielded(
                            asyncio.gather(heartbeat, return_exceptions=True),
                            propagate_cancellation=business_error is None,
                        )
        finally:
            self._active -= 1
            if not self._active:
                self._idle.set()

    async def record_diff(self, before, after, *, variable="diff", formatters=()) -> None:
        """把显式字段差异写入当前日志模板变量，转换失败单独报告，不改变业务结果。"""
        self.context.values()
        try:
            content = await DiffRenderer(self.settings, formatters).render(before, after)
        except Exception as error:
            self._failure(error)
            content = "[差异生成失败]"
        self.context.put(variable, content)

    async def _finalize(self, spec, operation, reservation, error, duration):
        try:
            values = self.context.values()
            values["outcome"] = "success" if error is None else "failure"
            if error is None and not self._condition(spec.condition, values):
                await self._write(lambda: self.provider.cancel(reservation))
                return
            success = error is None and self._condition(spec.success_condition, values)
            outcome = (
                "cancelled"
                if isinstance(error, asyncio.CancelledError)
                else "success"
                if success
                else "failure"
            )
            try:
                biz_no = self._render(spec.biz_no, values)
                if not biz_no:
                    raise ValueError("成功日志缺少业务编号")
            except (ValueError, KeyError, TemplateError):
                if success:
                    raise
                biz_no = None
            entry = LogRecordEntry(
                operation,
                outcome,
                duration,
                biz_no,
                self._render(spec.success if success else spec.fail, values),
                None if spec.extra is None else self._render(spec.extra, values),
            )
            await self._write(lambda: self.provider.finalize(reservation, entry))
            self.written += 1
        except (Exception, asyncio.CancelledError) as failure:
            self._failure(failure)

    def _render(self, template, values):
        result = Sanitizer.sanitize_text(self.expression.render_text(template, values))
        limit = self.settings.bizlog_max_length
        if len(result) > limit:
            result = result[: limit - len("[审计内容已截断]")] + "[审计内容已截断]"
        return result

    def _condition(self, template, values):
        if template is None:
            return True
        value = self.expression.eval_expression(template, values)
        if type(value) is not bool:
            raise ValueError("日志条件必须得到布尔值")
        return value

    async def _renew(self, reservation):
        while True:
            await asyncio.sleep(self.settings.bizlog_renew_seconds)
            try:
                await self._write(lambda: self.provider.renew(reservation))
            except Exception as error:
                self._failure(error)

    async def _cancel_reservation(self, reservation):
        try:
            await self._write(lambda: self.provider.cancel(reservation))
        except (Exception, asyncio.CancelledError) as error:
            self._failure(error)

    def _failure(self, error):
        self.failed += 1
        logger.error("业务审计交付失败：{}", type(error).__name__)

    async def close(self):
        self._closed = True
        await self._idle.wait()

    def resources(self):
        return {
            "active_operations": self._active,
            "written": self.written,
            "failed": self.failed,
            "closed": self._closed,
        }
