from framework.common.enums.base_enum import BaseEnum


class OutboxState(BaseEnum):
    """outbox 记录从入队到结算的生命周期状态。"""

    PENDING = ("pending", "待发布")
    SENDING = ("sending", "发布中")
    PUBLISHED = ("published", "已发布")
    DEAD = ("dead", "已终止")
    UNKNOWN = ("unknown", "结果未知")
    CANCELLED = ("cancelled", "已取消")
