from framework.common.enums.base_enum import BaseEnum


class TerminalEnum(BaseEnum):
    """请求来自哪一种客户端。"""

    UNKNOWN = (0, "未知")
    WECHAT_MINI_PROGRAM = (10, "微信小程序")
    WECHAT_WAP = (11, "微信公众号")
    H5 = (20, "H5 网页")
    APP = (31, "手机 App")
