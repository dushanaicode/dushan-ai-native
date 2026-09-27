from framework.common.enums import BaseEnum


class SmsChannelEnum(BaseEnum):
    """定义框架短信相关枚举值。"""

    DEBUG_DING_TALK = ("DEBUG_DING_TALK", "调试(钉钉)")
    ALIYUN = ("ALIYUN", "阿里云")
    TENCENT = ("TENCENT", "腾讯云")
    HUAWEI = ("HUAWEI", "华为云")
    QINIU = ("QINIU", "七牛云")
