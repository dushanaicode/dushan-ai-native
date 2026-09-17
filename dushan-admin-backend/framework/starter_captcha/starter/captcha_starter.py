from loguru import logger

from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_captcha.core.captcha_service import CaptchaService
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_di.decorators.components import starter


@starter
class CaptchaStarter:
    """校验挑战缓存与凭证契约，完成提供器和生成资源装配后开放验证码服务。"""

    def __init__(self, service: CaptchaService):
        self.service = service

    def open(self, provider=None):
        service = self.service
        settings = service.settings
        with service.startup(provider):
            logger.info("【CaptchaStarter 】开始初始化验证码资源")
            try:
                for ttl in (
                    settings.challenge_ttl_seconds,
                    settings.verification_ttl_seconds,
                    settings.generation_window_seconds,
                ):
                    service.store.cache.resolve_ttl_seconds(service.store.key, ttl)
                service.store.cache.get_client(service.store.key)
            except CacheException as error:
                raise CaptchaException(Codes.CACHE_UNAVAILABLE, cause=error) from error
            logger.info("【CaptchaStarter 】挑战与验证凭证缓存校验完成")
        logger.info(
            "【CaptchaStarter 】提供器与生成线程池已装配：{}", type(service._provider).__qualname__
        )
        logger.debug(
            "【CaptchaStarter 】用途={} 并发={} 挑战TTL={}s 凭证TTL={}s",
            settings.purposes,
            settings.generation_concurrency,
            settings.challenge_ttl_seconds,
            settings.verification_ttl_seconds,
        )
        logger.info("【CaptchaStarter 】初始化完成")

    async def close(self):
        await self.service.close()
        logger.info("【CaptchaStarter 】验证码资源已关闭")
