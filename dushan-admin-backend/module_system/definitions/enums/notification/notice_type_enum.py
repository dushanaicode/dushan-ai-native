from framework.common.enums.base_enum import BaseEnum


class NoticeTypeEnum(BaseEnum):
    SYSTEM = (1, "系统通知")
    USER = (2, "用户通知")
    TASK = (3, "任务通知")
    MESSAGE = (4, "消息通知")
    ALERT = (5, "警告通知")
