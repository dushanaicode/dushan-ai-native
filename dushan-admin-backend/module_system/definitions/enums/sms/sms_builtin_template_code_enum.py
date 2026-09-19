from framework.common.enums import BaseEnum


class SmsBuiltinTemplateCodeEnum(BaseEnum):
    """内置短信模板编码（不可删除/修改 code）"""

    ADMIN_SMS_LOGIN = ("admin-sms-login", "后台用户-手机号登录")
    USER_SMS_LOGIN = ("user-sms-login", "会员用户-手机号登陆")
    USER_UPDATE_MOBILE = ("user-update-mobile", "会员用户-修改手机")
    USER_UPDATE_PASSWORD = ("user-update-password", "会员用户-修改密码")
    USER_RESET_PASSWORD = ("user-reset-password", "会员用户-忘记密码")
    SYSTEM_NOTICE = ("system-notice", "系统通知")

    @classmethod
    def is_builtin(cls, code: str) -> bool:
        """判断指定 code 是否属于内置模板"""
        return any(item.code == code for item in cls)
