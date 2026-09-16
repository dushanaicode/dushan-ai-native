from framework.common.enums.base_enum import BaseEnum


class MessageState(BaseEnum):
    """单条消息一次消费处理的终态。"""

    SUCCEEDED = ("succeeded", "成功")
    RETRY = ("retry", "重试")
    REJECTED = ("rejected", "拒绝")
    UNKNOWN = ("unknown", "结果未知")
    CANCELLED = ("cancelled", "已取消")
