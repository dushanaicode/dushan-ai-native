from framework.common.enums.base_enum import BaseEnum


class LoggerLoginResultEnum(BaseEnum):
    SUCCESS = (0, "成功")
    BAD_CREDENTIALS = (10, "账号或密码不正确")
    USER_DISABLED = (20, "用户被禁用")
    CAPTCHA_NOT_FOUND = (30, "验证码不存在")
    CAPTCHA_CODE_ERROR = (31, "验证码不正确")
    UNKNOWN_EXCEPTION = (100, "未知异常")
