from framework.common.enums.base_enum import BaseEnum


class JobState(BaseEnum):
    """单次任务执行的终态。"""

    SUCCEEDED = ("succeeded", "成功")
    FAILED = ("failed", "失败")
    SKIPPED = ("skipped", "跳过")
    CANCELLED = ("cancelled", "已取消")
    TIMED_OUT = ("timed_out", "超时")
    UNKNOWN = ("unknown", "结果未知")
