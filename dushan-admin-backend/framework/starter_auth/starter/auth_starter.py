from collections.abc import Iterable

from loguru import logger

from framework.starter_auth.core.auth_service import AuthService
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_di.decorators.components import starter


@starter
class AuthStarter:
    """装配授权处理器、客户端与缓存，业务请求及 HTTP 资源由 AuthService 持有。"""

    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def open(self, *, components: Iterable[type] = (), transport=None) -> None:
        """全部装配校验成功后开放授权操作，不在启动时查询业务数据库或连接厂商。"""
        service = self.service
        settings, registry = service.settings, service.registry
        async with service.startup(transport=transport):
            logger.info("【AuthStarter 】开始初始化第三方授权")
            logger.info("【AuthStarter 】开始发现和注册授权处理器")
            registry.discover(components, allow_loopback_http=settings.allow_loopback_http)
            capabilities = sorted(registry.capabilities(), key=lambda item: item.source)
            implementations = {registry.get(item.source) for item in capabilities}
            for capability in capabilities:
                provider = registry.get(capability.source)
                logger.debug(
                    "【AuthStarter 】授权源={} 处理器={}.{} mode={} pkce={} oidc={} refresh={} revoke={}",
                    capability.source,
                    provider.__module__,
                    provider.__qualname__,
                    capability.mode,
                    capability.pkce,
                    capability.oidc,
                    capability.refresh,
                    capability.revoke,
                )
            logger.info(
                "【AuthStarter 】处理器注册完成：实现 {} 个，授权源 {} 个",
                len(implementations),
                len(capabilities),
            )

            logger.info("【AuthStarter 】开始校验静态客户端配置")
            for config in settings.clients:
                logger.debug(
                    "【AuthStarter 】静态客户端 application_id={} source={} enabled={}",
                    config.application_id,
                    config.source,
                    config.enabled,
                )
                if config.enabled:
                    provider = registry.get(config.source)
                    provider.validate_client(config, settings)
                    provider(config, None, service.credentials, None).validate_endpoints(settings)
            logger.info(
                "【AuthStarter 】静态客户端校验完成：启用 {} 个，停用 {} 个",
                sum(config.enabled for config in settings.clients),
                sum(not config.enabled for config in settings.clients),
            )
            logger.info(
                "【AuthStarter 】客户端提供器已接入：{}，客户端配置按授权请求读取",
                type(service.clients).__qualname__,
            )

            logger.info("【AuthStarter 】开始检查授权状态与应用凭据缓存")
            try:
                for key, ttl in zip(
                    settings.cache_keys(),
                    (settings.state_ttl_seconds, settings.credential_ttl_seconds),
                ):
                    service.store.cache.resolve_ttl_seconds(key, ttl)
                    service.store.cache.get_client(key)
                    logger.debug(
                        "【AuthStarter 】缓存前缀={} client={} ttl={}s",
                        key.key,
                        key.client_name,
                        ttl,
                    )
            except CacheException as error:
                raise AuthException(Codes.CACHE, cause=error) from error
            registry.seal()
            logger.info("【AuthStarter 】缓存检查完成，授权注册表已封存")
            logger.debug(
                "【AuthStarter 】HTTP 按需创建：超时={}s 最大连接数={}，授权操作超时={}s",
                settings.http_timeout_seconds,
                settings.max_connections,
                settings.operation_timeout_seconds,
            )
        logger.info("【AuthStarter 】初始化完成，第三方授权服务已就绪")

    async def close(self) -> None:
        """排空授权请求并关闭其持有的 HTTP 资源，保留失败及取消语义。"""
        logger.info("【AuthStarter 】开始关闭第三方授权服务，等待在途请求结束")
        await self.service.close()
        logger.info("【AuthStarter 】第三方授权服务已关闭")
