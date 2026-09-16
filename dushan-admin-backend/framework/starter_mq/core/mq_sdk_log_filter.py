import logging
from contextlib import contextmanager
from contextvars import ContextVar


class MQSdkLogFilter(logging.Filter):
    """仅处理当前 MQ 资源的 SDK 日志，保留安全警告并隔离原始帧。

    与 Auth/Monitor 的 SDK 适配一致：不改全局日志等级或 handler，每个应用独占
    ContextVar 和过滤器，SDK 后台任务继承其创建时的标记，关闭连接后才卸载。
    """

    _NAMES = (
        "aio_pika",
        "aio_pika.connection",
        "aio_pika.channel",
        "aio_pika.exchange",
        "aio_pika.queue",
        "aio_pika.message",
        "aio_pika.tools",
        "aiormq.connection",
        "aiormq.connection.marshall",
        "aiormq.channel",
        "aiokafka",
        "aiokafka.conn",
        "aiokafka.cluster",
        "aiokafka.admin.client",
        "aiokafka.consumer.consumer",
        "aiokafka.consumer.fetcher",
        "aiokafka.consumer.group_coordinator",
        "aiokafka.consumer.subscription_state",
        "aiokafka.producer.producer",
        "aiokafka.producer.sender",
        "aiokafka.helpers",
        "aiokafka.coordinator.assignors.abstract",
        "aiokafka.coordinator.assignors.roundrobin",
        "aiokafka.coordinator.assignors.range",
        "aiokafka.coordinator.assignors.sticky.partition_movements",
        "aiokafka.coordinator.assignors.sticky.sticky_assignor",
    )

    def __init__(self):
        super().__init__()
        self._quiet = ContextVar("mq_sdk_quiet", default=False)

    def filter(self, record):
        if not self._quiet.get():
            return True
        if record.levelno < logging.WARNING:
            return False
        return logging.LogRecord(
            record.name,
            record.levelno,
            record.pathname,
            record.lineno,
            "MQ SDK 诊断：连接或协议操作异常，原始帧已隔离",
            (),
            None,
            record.funcName,
        )

    def open(self):
        for name in self._NAMES:
            logging.getLogger(name).addFilter(self)

    def close(self):
        for name in self._NAMES:
            logging.getLogger(name).removeFilter(self)

    @contextmanager
    def quiet(self):
        token = self._quiet.set(True)
        try:
            yield
        finally:
            self._quiet.reset(token)
