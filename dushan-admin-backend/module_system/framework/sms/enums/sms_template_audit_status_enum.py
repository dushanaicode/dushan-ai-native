from framework.common.enums import BaseEnum


class SmsTemplateAuditStatusEnum(BaseEnum):
    """定义框架短信相关枚举值。"""

    CHECKING = (1, "审核中")
    SUCCESS = (2, "审核通过")
    FAIL = (3, "审核失败")
