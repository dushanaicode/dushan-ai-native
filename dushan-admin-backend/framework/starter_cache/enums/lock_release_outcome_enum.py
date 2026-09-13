from framework.common.enums.base_enum import BaseEnum


class LockReleaseOutcomeEnum(BaseEnum):
    """Redis 租约锁原子释放脚本返回的终态；只有 RELEASED 表示本进程按时释放。"""

    RELEASED = ("released", "释放成功")
    MISSING = ("missing", "锁已不存在")
    LOST_OWNER = ("lost_owner", "锁所有权已丢失")
