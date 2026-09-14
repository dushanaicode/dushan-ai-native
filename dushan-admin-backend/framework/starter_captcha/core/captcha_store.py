import hashlib

from pydantic import ValidationError

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.definitions.captcha_cache_keys import CaptchaCacheKeys
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_record import CaptchaRecord


class CaptchaStore:
    """挑战与凭证的有期状态；Lua 负责计数、挑战转换和凭证消费的线性化点。

    键只由用途、种类和令牌摘要决定，不含应用实例标识：同一服务的多个 worker
    因此共享同一份状态，挑战在哪个进程生成、在哪个进程校验都成立，部署不需要
    会话亲和。令牌本身是 32 字节随机值，其摘要已足以保证键不可猜测；
    若要把多套部署彻底隔开，应当在 Cache 配置里给它们不同的 client/db。
    """

    _RATE = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind ~= 'none' and kind ~= 'string' then return -1 end
local raw = redis.call('GET', KEYS[1])
if raw and (not tonumber(raw) or redis.call('PTTL', KEYS[1]) <= 0) then return -1 end
local count = tonumber(raw) or 0
if count < 0 or count ~= math.floor(count) then return -1 end
if count >= tonumber(ARGV[1]) then return 0 end
redis.call('INCR', KEYS[1])
if count == 0 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return 1
"""
    _CREATE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], 'payload', ARGV[1], 'remaining', ARGV[2])
redis.call('EXPIRE', KEYS[1], ARGV[3])
return 1
"""
    _RESERVE = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind == 'none' then return {0} end
if kind ~= 'hash' then return {-2} end
local data = redis.call('HMGET', KEYS[1], 'payload', 'remaining')
local remaining = tonumber(data[2])
if not data[1] or not remaining or remaining < 0 or remaining > tonumber(ARGV[1])
   or remaining ~= math.floor(remaining) or redis.call('PTTL', KEYS[1]) <= 0 then
    return {-2}
end
if remaining == 0 then return {-1} end
redis.call('HINCRBY', KEYS[1], 'remaining', -1)
return {1, data[1], remaining - 1}
"""
    _COMPLETE = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind == 'none' then return 0 end
if kind ~= 'hash' or redis.call('HGET', KEYS[1], 'payload') ~= ARGV[1]
   or redis.call('PTTL', KEYS[1]) <= 0 then return -1 end
if redis.call('EXISTS', KEYS[2]) == 1 then return -1 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('DEL', KEYS[1])
return 1
"""
    _CONSUME = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind == 'none' then return 0 end
if kind ~= 'string' or redis.call('GET', KEYS[1]) ~= ARGV[1]
   or redis.call('PTTL', KEYS[1]) <= 0 then return -1 end
redis.call('DEL', KEYS[1])
return 1
"""

    def __init__(self, cache: CacheHandler, settings: CaptchaSettings) -> None:
        self.cache = cache
        self.settings = settings
        self.key = CaptchaCacheKeys.state(settings.client_name)

    def identifier(self, purpose: str, kind: str, token: str) -> str:
        """缓存键只保存令牌摘要；用途边界在读取前确定。"""
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        return f"{purpose}:{kind}:{digest}"

    async def _eval(self, identifiers: tuple[str, ...], script: str, args=()):
        try:
            return await self.cache.eval_atomic(self.key, identifiers, script, args)
        except CacheException as error:
            raise CaptchaException(Codes.CACHE_UNAVAILABLE, cause=error) from error

    async def reserve_generation(self) -> None:
        """限制整个部署的生成量，TTL 与计数在一次 Redis 操作内建立。

        计数键不含实例标识，因此多 worker 共用同一个配额，而不是每进程各算一份。
        """
        result = await self._eval(
            ("generation",),
            self._RATE,
            (self.settings.generation_limit, self.settings.generation_window_seconds),
        )
        if result != 1:
            raise CaptchaException(Codes.CAPACITY if result == 0 else Codes.CORRUPT)

    async def create(self, token: str, record: CaptchaRecord) -> None:
        result = await self._eval(
            (self.identifier(record.purpose, "challenge", token),),
            self._CREATE,
            (
                record.model_dump_json(),
                self.settings.max_attempts,
                self.settings.challenge_ttl_seconds,
            ),
        )
        if result != 1:
            raise CaptchaException(Codes.CORRUPT)

    async def reserve(self, token: str, purpose: str) -> tuple[CaptchaRecord, str, int]:
        result = await self._eval(
            (self.identifier(purpose, "challenge", token),),
            self._RESERVE,
            (self.settings.max_attempts,),
        )
        if result[0] != 1:
            raise CaptchaException(
                {0: Codes.EXPIRED, -1: Codes.EXHAUSTED, -2: Codes.CORRUPT}[result[0]]
            )
        try:
            record = CaptchaRecord.model_validate_json(result[1])
        except ValidationError as error:
            raise CaptchaException(Codes.CORRUPT, cause=error) from error
        expected_count = {"block_puzzle": 1, "click_word": 3, "aliyun": 0, "tencent": 0}[
            self.settings.provider
        ]
        if (
            record.purpose != purpose
            or record.provider != self.settings.provider
            or len(record.points) != expected_count
        ):
            raise CaptchaException(Codes.CORRUPT)
        return record, result[1], result[2]

    async def complete(self, token: str, purpose: str, payload: str, verification: str) -> None:
        result = await self._eval(
            (
                self.identifier(purpose, "challenge", token),
                self.identifier(purpose, "verification", verification),
            ),
            self._COMPLETE,
            (payload, self.settings.provider, self.settings.verification_ttl_seconds),
        )
        if result != 1:
            raise CaptchaException(Codes.EXPIRED if result == 0 else Codes.CORRUPT)

    async def consume(self, verification: str, purpose: str) -> None:
        result = await self._eval(
            (self.identifier(purpose, "verification", verification),),
            self._CONSUME,
            (self.settings.provider,),
        )
        if result != 1:
            raise CaptchaException(Codes.INVALID_VERIFICATION if result == 0 else Codes.CORRUPT)
