from loguru import logger

from framework.starter_mq.core.backend_capabilities import BackendCapabilities
from framework.starter_mq.enums.exhausted_policy import ExhaustedPolicy
from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.enums.tenant_policy import TenantPolicy
from framework.starter_mq.exception.mq_exception import MQException


class ConsumerRegistry:
    """启动时一次验证声明和覆盖；不从存储里的类名重建可执行对象。"""

    def __init__(self, settings, handlers):
        logger.info("【MQStarter 】开始校验消费者声明")
        self.settings = settings
        self.handlers = {}
        self.limits = {}
        self.ignored_overrides = ()
        bindings = set()
        for handler in handlers:
            definition = vars(handler)["__mq_consumer__"]
            if definition.key in self.handlers:
                error = MQException("declaration")
                error.add_note("重复消费者 key: " + definition.key)
                raise error
            self._validate(definition)
            binding = (definition.destination, definition.group)
            if definition.mode is not MessageMode.PUBSUB:
                if binding in bindings:
                    raise MQException("declaration")
                bindings.add(binding)
            self.handlers[definition.key] = handler
            logger.debug(
                "【MQStarter 】消费者={} destination={} group={} mode={} handler={}.{}",
                definition.key,
                definition.destination,
                definition.group,
                definition.mode.value,
                handler.__module__,
                handler.__qualname__,
            )
        if len(self.handlers) > settings.max_consumers:
            raise MQException("declaration")
        logger.info("【MQStarter 】消费者声明校验完成：{} 个", len(self.handlers))

    def _validate(self, definition):
        try:
            capability = BackendCapabilities.for_mode(self.settings.backend, definition.mode)
        except ValueError as error:
            raise MQException("declaration", cause=error) from error
        grouped = definition.mode in {MessageMode.STREAM, MessageMode.TOPIC}
        if grouped != bool(definition.group):
            raise MQException("declaration")
        if not capability.acknowledged and (
            definition.retry.count or definition.exhausted is not ExhaustedPolicy.DISCARD
        ):
            raise MQException("declaration")
        if definition.retry.max_delay_seconds > self.settings.max_retry_delay_seconds:
            raise MQException("declaration")
        if definition.session_policy is None and not definition.workload_capabilities:
            raise MQException("declaration")
        if definition.session_policy is not None and (
            not definition.session_policy.requires_identity
            or definition.tenant_policy is not TenantPolicy.REQUIRED
        ):
            raise MQException("declaration")
        if definition.external_authenticator is not None and not callable(
            getattr(definition.external_authenticator, "authenticate", None)
        ):
            raise MQException("declaration")

    def apply(self, overrides):
        unknown = sorted(set(overrides) - self.handlers.keys())
        if unknown and self.settings.unknown_override == "fail":
            error = MQException("declaration")
            error.add_note("未知消费者覆盖: " + ", ".join(unknown[:16]))
            raise error
        self.ignored_overrides = tuple(unknown)
        for key, handler in self.handlers.items():
            override = overrides.get(key)
            enabled = override is None or override.enabled is not False
            concurrency = self.settings.concurrency
            prefetch = self.settings.prefetch
            if override is not None:
                if override.concurrency is not None:
                    concurrency = override.concurrency
                if override.prefetch is not None:
                    prefetch = override.prefetch
            if (
                not 1 <= concurrency <= self.settings.max_concurrency
                or not concurrency <= prefetch <= self.settings.max_prefetch
            ):
                raise MQException("declaration")
            self.limits[key] = (enabled, concurrency, prefetch)
            logger.debug(
                "【MQStarter 】消费者={} enabled={} concurrency={} prefetch={}",
                key,
                enabled,
                concurrency,
                prefetch,
            )
        logger.info(
            "【MQStarter 】消费者运行配置已绑定：启用 {} 个，停用 {} 个",
            len(self.active()),
            len(self.handlers) - len(self.active()),
        )

    def active(self):
        return [handler for key, handler in self.handlers.items() if self.limits[key][0]]
