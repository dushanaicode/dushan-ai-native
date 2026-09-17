from framework.starter_cache.enums.cache_namespace import CacheNamespace
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_di.decorators.components import framework


@framework(providers=[CacheKeyContainer])
class SystemCacheKeys(CacheKeyContainer):
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
        namespace=CacheNamespace.GLOBAL,
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
