from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_scanner.annotation.scanner_decorator import scanner


@scanner
class CaptchaCacheKeys(CacheKeyContainer):
    """验证码占用的缓存前缀声明。

    在这里静态声明而不是运行时内联构造 CacheKey，是为了让前缀进入
    CacheKeyRegistry 的启动校验：重复前缀、互相包含的前缀（例如某个业务模块
    再声明一个 captcha:xxx）会在启动阶段直接失败，而不是等到某次整段失效
    互相清空数据才被发现。

    client_name 是这里的默认值，实际使用哪个客户端由 captcha.client_name 决定；
    前缀由本声明固定，客户端由配置选择。
    """

    STATE = CacheKey(
        key="captcha",
        remark="验证码挑战与一次性业务凭证",
        client_name="default",
    )
