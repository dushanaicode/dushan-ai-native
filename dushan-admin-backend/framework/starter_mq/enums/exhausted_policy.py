from framework.common.enums.base_enum import BaseEnum


class ExhaustedPolicy(BaseEnum):
    """重试次数耗尽后的处理方式。"""

    DEAD_LETTER = ("dead_letter", "转入死信")
    DISCARD = ("discard", "丢弃")
    HOLD = ("hold", "保留待处理")
