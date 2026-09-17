from framework.common.enums.base_enum import BaseEnum


class SmsChannelEnum(BaseEnum):
    """定义框架短信相关枚举值。"""

    DEBUG_DING_TALK = ("DEBUG_DING_TALK", "调试(钉钉)")
    ALIYUN = ("ALIYUN", "阿里云")
    TENCENT = ("TENCENT", "腾讯云")
    HUAWEI = ("HUAWEI", "华为云")
    QINIU = ("QINIU", "七牛云")

    @classmethod
    def get_by_code(cls, code: str):
        """根据渠道编码返回对应的枚举项"""
        for item in cls:
            if item.code == code:
                return item
        return None
