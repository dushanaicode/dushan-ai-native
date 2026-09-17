from framework.common.enums.base_enum import BaseEnum


class SmsTemplateTypeEnum(BaseEnum):
    VERIFICATION_CODE = (1, "验证码")
    NOTICE = (2, "通知")
    PROMOTION = (3, "营销")
