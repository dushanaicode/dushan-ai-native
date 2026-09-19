from framework.common.enums.base_enum import BaseEnum


class JobTriggerKind(BaseEnum):
    """一次执行请求的触发来源。"""

    SCHEDULED = ("scheduled", "定时触发")
    MANUAL = ("manual", "手动触发")
