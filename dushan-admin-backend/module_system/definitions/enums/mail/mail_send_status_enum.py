from framework.common.enums import BaseEnum


class MailSendStatusEnum(BaseEnum):
    """定义邮件相关枚举值。"""

    INIT = (0, "初始化")
    SENDING = (5, "发送中，结果可能未知")
    SUCCESS = (10, "发送成功")
    FAILURE = (20, "发送失败")
    IGNORE = (30, "忽略，即不发送")
    CANCELLED = (40, "租户不可用，已取消")
