from framework.common.enums.base_enum import BaseEnum


class NotificationChannelEnum(BaseEnum):
    INTERNAL = ("INTERNAL", "站内信")
    IM = ("IM", "IM 私聊")
    SMS = ("SMS", "短信")
    MAIL = ("MAIL", "邮件")
    WECHAT = ("WECHAT", "微信公众号")
    DINGTALK = ("DINGTALK", "钉钉")
