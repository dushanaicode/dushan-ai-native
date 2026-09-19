from framework.common.enums.base_enum import BaseEnum


class MQBackend(BaseEnum):
    """消息运行时实际连接的后端类型。"""

    REDIS = ("redis", "Redis")
    RABBITMQ = ("rabbitmq", "RabbitMQ")
    KAFKA = ("kafka", "Kafka")
