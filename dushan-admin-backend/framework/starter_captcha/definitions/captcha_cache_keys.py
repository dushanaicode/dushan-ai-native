from framework.starter_cache.model.cache_key import CacheKey


class CaptchaCacheKeys:
    """启动登记与运行共用同一声明；客户端必须来自当前应用配置。"""

    @staticmethod
    def state(client_name: str) -> CacheKey:
        return CacheKey(
            key="captcha",
            remark="验证码挑战与一次性业务凭证",
            client_name=client_name,
        )
