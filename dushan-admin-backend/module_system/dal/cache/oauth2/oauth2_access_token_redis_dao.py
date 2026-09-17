from datetime import datetime, timezone
from math import ceil

from framework.starter_cache.repository.base_cache_dao import BaseCacheDAO
from framework.starter_di.decorators.components import dao
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO


@dao
class OAuth2AccessTokenRedisDAO(BaseCacheDAO):
    """仅缓存摘要到记录编号的定位结果；有效性必须重新读取主库。"""

    def __init__(self):
        super().__init__(SystemCacheKeys.OAUTH2_ACCESS_TOKEN)

    @staticmethod
    def identifier(tenant_id: str, token_digest: str) -> str:
        return f"{tenant_id}:{token_digest}"

    async def cache_token(self, token: OAuth2AccessTokenDO) -> bool:
        identifier = self.identifier(token.tenant_id, token.token_digest)
        ttl = ceil(
            (token.expires_time - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()
        )
        if ttl <= 0 or token.revoked:
            await self.delete(identifier)
            return False
        await self.set(identifier, token.id, ttl_seconds=ttl)
        return True
