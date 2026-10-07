from framework.starter_cache.public import CacheKey, CacheKeyContainer, CacheNamespace
from framework.starter_di.public import (
    framework,
)


@framework(providers=[CacheKeyContainer])
class SystemCacheKeyConstants(CacheKeyContainer):
    QR_LOGIN = CacheKey(
        key="system:qr_login",
        remark="第一方扫码登录票据，原子状态及浏览器/租户绑定",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
    )
    SOCIAL_CALLBACK_RELAY = CacheKey(
        key="system:social_callback_relay",
        remark="按服务端state转交厂商表单回调",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=300,
    )
    SOCIAL_LOGIN_TENANT = CacheKey(
        key="system:social_login_tenant",
        remark="按安全浏览器绑定定位社交授权租户",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=300,
    )
    EMAIL_PASSWORD_RESET = CacheKey(
        key="system:email_password_reset",
        remark="邮箱找回密码校验与发送计数",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=86400,
    )
    SMS_CODE_ATTEMPTS = CacheKey(
        key="system:sms_code_attempts",
        remark="单条短信验证码的校验次数，原子脚本按有效期设置过期",
        client_name="default",
        namespace=CacheNamespace.TENANT,
    )
    WEBSOCKET_TICKET = CacheKey(
        key="system:websocket_ticket",
        remark="一次性 WebSocket 会话票据",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=60,
    )
    DEPT_CHILDREN_ID_LIST = CacheKey(
        key="system:dept_children_ids",
        remark="指定部门的所有子部门编号数组",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    ROLE = CacheKey(
        key="system:role",
        remark="角色信息",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    USER_ROLE_ID_LIST = CacheKey(
        key="system:user_role_ids",
        remark="用户拥有的角色编号集合",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    USER_MENU_LIST = CacheKey(
        key="system:user_menu_ids",
        remark="用户拥有的菜单编号集合",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    MENU_ROLE_ID_LIST = CacheKey(
        key="system:menu_role_ids",
        remark="拥有指定菜单的角色编号集合",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    PERMISSION_MENU_ID_LIST = CacheKey(
        key="system:permission_menu_ids",
        remark="拥有权限对应的菜单编号数组",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    OAUTH_CLIENT = CacheKey(
        key="system:oauth_client",
        remark="OAuth2 客户端信息",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    OAUTH2_ACCESS_TOKEN = CacheKey(
        key="system:oauth2_access_token",
        remark="OAuth2 访问令牌",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=3600,
    )
    NOTIFY_TEMPLATE = CacheKey(
        key="system:notify_template",
        remark="站内信模版",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    MAIL_ACCOUNT = CacheKey(
        key="system:mail_account",
        remark="邮件账号",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=3600,
    )
    MAIL_TEMPLATE = CacheKey(
        key="system:mail_template",
        remark="邮件模版",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=3600,
    )
    SMS_TEMPLATE = CacheKey(
        key="system:sms_template",
        remark="短信模版",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    WXA_SUBSCRIBE_TEMPLATE = CacheKey(
        key="system:wxa_subscribe_template",
        remark="小程序订阅模版",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=3600,
    )
    SOCIAL_CLIENT = CacheKey(
        key="system:social_client",
        remark="授权客户端信息",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=3600,
    )
    TENANT_PACKAGE = CacheKey(
        key="system:tenant_package",
        remark="租户套餐信息",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=3600,
    )
