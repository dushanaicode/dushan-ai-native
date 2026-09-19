from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class MQErrorCodes:
    """消息队列错误段 1_010_000～1_010_999。"""

    ERROR = ErrorCode(code=1_010_000, description="消息队列异常", message_key="mq.error")
    CONFIGURATION = ErrorCode(
        code=1_010_001,
        description="MQ 配置、声明或提供者未就绪",
        message_key="mq.configuration",
    )
    CLOSED = ErrorCode(code=1_010_002, description="MQ 运行时不可用", message_key="mq.closed")
    CAPACITY = ErrorCode(
        code=1_010_003,
        description="MQ 容量已满，发布被拒绝",
        message_key="mq.capacity",
    )
    UNKNOWN = ErrorCode(
        code=1_010_004,
        description="MQ 发布或执行结果未知",
        message_key="mq.unknown",
    )
    CONFIRMATION = ErrorCode(
        code=1_010_005,
        description="MQ 后端未确认消息",
        message_key="mq.confirmation",
    )
    LEASE = ErrorCode(code=1_010_006, description="MQ 消费租约已失效", message_key="mq.lease")

    DECLARATION = ErrorCode(
        code=1_010_011,
        description="MQ 消费声明重复或不受后端支持",
        message_key="mq.declaration",
    )
    INVALID = ErrorCode(
        code=1_010_012,
        description="MQ 消息格式或大小无效",
        message_key="mq.invalid",
    )
    AUTHENTICATION = ErrorCode(
        code=1_010_013,
        description="MQ 消息认证失败",
        message_key="mq.authentication",
    )
    EXPIRED = ErrorCode(code=1_010_014, description="MQ 消息已过期", message_key="mq.expired")
    CONFLICT = ErrorCode(
        code=1_010_015,
        description="MQ 消息标识与既有内容冲突",
        message_key="mq.conflict",
    )
