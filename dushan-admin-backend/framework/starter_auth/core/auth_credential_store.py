from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.distributed_lock import DistributedLock


class AuthCredentialStore:
    """仅缓存厂商应用凭据；命名空间含应用、来源和配置摘要，不保存本站登录态。"""

    def __init__(self, cache: CacheHandler, locks: DistributedLock, settings: AuthSettings):
        self.cache, self.locks, self.settings = cache, locks, settings
        self.key = settings.cache_keys()[1]

    async def get_or_load(self, config: AuthClientConfig, loader) -> str:
        identifier = f"{self.settings.namespace}:{config.application_id}:{config.source}:{config.fingerprint()}"
        try:
            cached = await self.cache.get(self.key, identifier)
            if cached.hit:
                return self._credential(cached.value)
            budget = self.settings.operation_timeout_seconds
            async with self.locks.with_lock(
                "auth:" + identifier,
                client_name=self.settings.client_name,
                lease_seconds=budget + 5,
                wait_seconds=budget,
                critical_section_timeout_seconds=budget,
            ):
                cached = await self.cache.get(self.key, identifier)
                if cached.hit:
                    return self._credential(cached.value)
                generation = await self.cache.capture_generation(self.key)
                credential, expires_in = await loader()
                ttl = min(
                    expires_in - self.settings.credential_expiry_margin_seconds,
                    self.settings.credential_ttl_seconds,
                )
                if ttl <= 0:
                    raise AuthException(Codes.RESPONSE, outcome="unknown")
                published = await self.cache.publish_loaded_value(
                    self.key,
                    identifier,
                    self._credential(credential),
                    generation,
                    ttl,
                )
                if not published:
                    raise AuthException(Codes.CACHE, outcome="unknown")
                return credential
        except CacheException as error:
            raise AuthException(Codes.CACHE, outcome="unknown", cause=error) from error

    @staticmethod
    def _credential(value) -> str:
        if not isinstance(value, str) or not value:
            raise AuthException(Codes.RESPONSE)
        return value
