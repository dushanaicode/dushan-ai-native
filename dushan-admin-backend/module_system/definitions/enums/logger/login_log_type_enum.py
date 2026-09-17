from framework.common.enums.base_enum import BaseEnum


class LoginLogTypeEnum(BaseEnum):
    LOGIN_USERNAME = (1, "使用账号登录")
    LOGIN_SOCIAL = (2, "使用社交登录")
    LOGIN_MOBILE = (3, "使用手机登陆")
    LOGIN_SMS = (4, "使用短信登陆")
    LOGOUT_SELF = (20, "自己主动登出")
    LOGOUT_DELETE = (21, "强制退出")
