from framework.common.enums.base_enum import BaseEnum


class SecurityRealm(BaseEnum):
    """本站主体的权限域；公开是路由属性，不是一种可信身份。"""

    ACCOUNT = ("account", "本站账号")
    TENANT = ("tenant", "租户身份")
    PLATFORM = ("platform", "平台操作身份")
    SUPPORT = ("support", "支持会话")
