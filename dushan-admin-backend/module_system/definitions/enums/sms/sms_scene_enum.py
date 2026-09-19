from framework.common.enums import BaseEnum


class SmsSceneEnum(BaseEnum):
    """
    短信场景枚举

    枚举项格式: (code, label, template_code)
    - code: 场景编码
    - label: 场景名称
    - template_code: 场景对应的模板代码
    """

    MEMBER_LOGIN = (1, "会员用户 - 手机号登陆", "user-sms-login")
    MEMBER_UPDATE_MOBILE = (2, "会员用户 - 修改手机", "user-update-mobile")
    MEMBER_UPDATE_PASSWORD = (3, "会员用户 - 修改密码", "user-update-password")
    MEMBER_RESET_PASSWORD = (4, "会员用户 - 忘记密码", "user-reset-password")
    ADMIN_MEMBER_LOGIN = (21, "后台用户 - 手机号登录", "admin-sms-login")
    ADMIN_MEMBER_REGISTER = (22, "后台用户 - 手机号注册", "admin-sms-register")
    ADMIN_MEMBER_RESET_PASSWORD = (23, "后台用户 - 忘记密码", "admin-reset-password")
    ADMIN_MEMBER_UPDATE_MOBILE = (24, "后台用户 - 绑定手机号", "admin-update-mobile")

    def __new__(cls, code: int, label: str, template_code: str):
        member = object.__new__(cls)
        member._value_ = code
        member._label_ = label
        member._template_code_ = template_code
        return member

    @property
    def template_code(self) -> str:
        """
        获取此短信场景的模板代码 (例如: "user-sms-login")。
        """
        return self._template_code_

    @classmethod
    def get_all_codes_as_list(cls) -> list[int]:
        """返回所有枚举项的 code 列表"""
        return sorted(item.code for item in cls)

    @classmethod
    def get_all_template_codes(cls) -> list[str]:
        """返回所有枚举项的 template_code 列表"""
        return [item.template_code for item in cls]

    @classmethod
    def get_code_by_scene(cls, target_code: int) -> "SmsSceneEnum | None":
        """根据 code 值获取对应的枚举成员实例"""
        return cls.get_by_code(target_code)
