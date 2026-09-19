import hashlib
import re

from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_flow import AuthFlow
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_exception import CacheException


class AuthStateStore:
    """同一次授权的全部安全材料共同写入、匹配和消费；跨 worker 不依赖内存。"""

    _CREATE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], 'binding', ARGV[1], 'client', ARGV[2],
           'verifier', ARGV[3], 'nonce', ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""
    _CONSUME = """
if redis.call('TYPE', KEYS[1]).ok ~= 'hash' or redis.call('PTTL', KEYS[1]) <= 0 then
    return {0}
end
local values = redis.call('HMGET', KEYS[1], 'binding', 'client', 'verifier', 'nonce')
if values[1] ~= ARGV[1] or values[2] ~= ARGV[2] or not values[3] or not values[4] then
    return {0}
end
redis.call('DEL', KEYS[1])
return {1, values[3], values[4]}
"""

    def __init__(self, cache: CacheHandler, settings: AuthSettings):
        self.cache = cache
        self.settings = settings
        self.key = settings.cache_keys()[0]

    def identifier(self, client: AuthClientConfig, state: str) -> str:
        if not isinstance(state, str) or re.fullmatch(r"[0-9a-f]{64}", state) is None:
            raise AuthException(Codes.STATE)
        digest = hashlib.sha256(state.encode("ascii")).hexdigest()
        return f"{self.settings.namespace}:{client.application_id}:{client.source}:{digest}"

    @staticmethod
    def binding_digest(binding: str) -> str:
        # binding 来自业务端受保护的浏览器会话/一次性 cookie，不能用 IP 或请求 state 代替。
        if not isinstance(binding, str) or not 32 <= len(binding) <= 1024:
            raise AuthException(Codes.INPUT)
        return hashlib.sha256(binding.encode()).hexdigest()

    async def create(self, client: AuthClientConfig, binding: str, flow: AuthFlow) -> None:
        result = await self._eval(
            client,
            flow.state,
            self._CREATE,
            (
                self.binding_digest(binding),
                client.fingerprint(),
                flow.verifier,
                flow.nonce,
                self.settings.state_ttl_seconds,
            ),
        )
        if result != 1:
            raise AuthException(Codes.STATE)

    async def consume(self, client: AuthClientConfig, binding: str, state: str) -> AuthFlow:
        result = await self._eval(
            client,
            state,
            self._CONSUME,
            (self.binding_digest(binding), client.fingerprint()),
        )
        if result[0] != 1:
            raise AuthException(Codes.STATE)
        return AuthFlow(state=state, verifier=result[1], nonce=result[2])

    async def _eval(self, client, state, script, args):
        identifier = self.identifier(client, state)
        try:
            return await self.cache.eval_atomic(self.key, (identifier,), script, args)
        except CacheException as error:
            raise AuthException(Codes.CACHE, outcome="unknown", cause=error) from error
