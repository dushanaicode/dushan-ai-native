from framework.common.enums.base_enum import BaseEnum


class MessageMode(BaseEnum):
    """消费定义对应的后端投递模式。"""

    STREAM = ("stream", "Redis Stream")
    PUBSUB = ("pubsub", "Redis 发布订阅")
    QUEUE = ("queue", "RabbitMQ 队列")
    TOPIC = ("topic", "Kafka 主题")
