import asyncio
import math
import uuid

from redis.asyncio import Redis
from redis.exceptions import RedisError

from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.enums.lock_release_outcome_enum import (
    LockReleaseOutcomeEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException

_ACQUIRE_RETRY_INTERVAL_SECONDS = 0.05
_MAX_LEASE_MILLISECONDS = (1 << 63) - 1

# 释放时必须确认持有者仍是自己：租约可能已经超时并被别人重新获取，
# 这时直接 DEL 会解开别人的锁。脚本用三种返回值区分这三类终态。
_RELEASE_SCRIPT = """
-- cache_lock_release
local current_owner = redis.call('GET', KEYS[1])
if current_owner == false then
    return ARGV[3]
end
if current_owner ~= ARGV[1] then
    return ARGV[4]
end
redis.call('DEL', KEYS[1])
return ARGV[2]
"""


class RedisLeaseLock:
    """绑定单个持有者令牌的不可重入 Redis 租约锁。

    租约必须是有限时长：持有者进程崩溃时锁要能自动过期，否则整个前缀会被永久堵住。
    实例只允许一次获取尝试，释放后不可复用，避免同一个令牌被两段逻辑共用。
    """

    def __init__(
        self,
        client: Redis,
        key: str,
        lease_seconds: float,
        wait_seconds: float,
        *,
        command_timeout_seconds: float | None = None,
    ) -> None:
        self._client = client
        self._key = key
        self._lease_seconds = self.validate_seconds(
            lease_seconds, "lease_seconds", allow_zero=False
        )
        self._lease_milliseconds = self._to_lease_milliseconds(self._lease_seconds)
        self._wait_seconds = self.validate_seconds(wait_seconds, "wait_seconds", allow_zero=True)
        # 调用方可收紧单次命令上界；None 沿用 Cache 客户端自身的连接/读写超时。
        self._command_timeout_seconds = (
            None
            if command_timeout_seconds is None
            else self.validate_seconds(
                command_timeout_seconds, "command_timeout_seconds", allow_zero=False
            )
        )
        self._owner_token = uuid.uuid4().hex
        self._acquire_started = False
        self._acquired = False
        self._lease_deadline: float | None = None

    @property
    def key(self) -> str:
        """锁在 Redis 中的物理键。"""
        return self._key

    @property
    def owner_token(self) -> str:
        """本次租约身份，供受控执行请求认领使用；不得输出到日志。"""
        return self._owner_token

    @property
    def release_required(self) -> bool:
        """取得过租约且尚未 CAS 释放，不等同于远端租约仍有效。"""
        return self._acquired

    @property
    def is_valid(self) -> bool:
        return (
            self._acquired
            and self._lease_deadline is not None
            and asyncio.get_running_loop().time() < self._lease_deadline
        )

    async def renew(self) -> bool:
        """只续当前 owner，使用发起时刻估算期限；已过期的本地租约不能复活。"""
        if not self.is_valid:
            return False
        started = asyncio.get_running_loop().time()
        try:
            async with asyncio.timeout(self._command_timeout_seconds):
                result = await self._client.eval(
                    "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('PEXPIRE',KEYS[1],ARGV[2]) else return 0 end",
                    1,
                    self._key,
                    self._owner_token,
                    self._lease_milliseconds,
                )
        except (RedisError, TimeoutError) as error:
            self._lease_deadline = None
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="Redis 续租失败", cause=error
            ) from error
        if result != 1:
            self._lease_deadline = None
            return False
        self._lease_deadline = started + self._lease_seconds
        return self.is_valid

    async def acquire(self) -> bool:
        """在等待上界内用 SET NX PX 获取租约，超时返回 False 而不是抛错。"""
        if self._acquire_started:
            raise CacheException(CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="锁实例不支持重复获取")
        self._acquire_started = True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._wait_seconds
        while True:
            attempt_started_at = loop.time()
            try:
                async with asyncio.timeout(self._command_timeout_seconds):
                    acquired = await self._client.set(
                        self._key, self._owner_token, nx=True, px=self._lease_milliseconds
                    )
            except (RedisError, TimeoutError) as error:
                raise CacheException(
                    CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="Redis 获取租约锁失败", cause=error
                ) from error
            if acquired:
                self._acquired = True
                # 以发起请求的时刻计算到期时间，保证估计值不晚于 Redis 端的真实到期。
                self._lease_deadline = attempt_started_at + self._lease_seconds
                return True
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(_ACQUIRE_RETRY_INTERVAL_SECONDS, remaining))

    async def release(self) -> LockReleaseOutcomeEnum:
        """屏蔽调用方取消，直到原子释放得到终态，避免留下没人释放的锁。"""
        if not self._acquired:
            raise CacheException(CacheErrorCodes.LOCK_RELEASE_FAILED, msg="锁实例尚未获取或已释放")
        return await AsyncioUtils.run_cancellation_shielded(self._release_once())

    async def _release_once(self) -> LockReleaseOutcomeEnum:
        """执行一次原子释放并解释返回值。"""
        try:
            async with asyncio.timeout(self._command_timeout_seconds):
                result = await self._client.eval(
                    _RELEASE_SCRIPT,
                    1,
                    self._key,
                    self._owner_token,
                    LockReleaseOutcomeEnum.RELEASED.code,
                    LockReleaseOutcomeEnum.MISSING.code,
                    LockReleaseOutcomeEnum.LOST_OWNER.code,
                )
        except (RedisError, TimeoutError) as error:
            raise CacheException(
                CacheErrorCodes.LOCK_RELEASE_FAILED,
                msg="Redis 释放租约锁失败",
                cause=error,
            ) from error
        outcome = self._parse_release_outcome(result)
        self._acquired = False
        self._lease_deadline = None
        return outcome

    def get_critical_deadline(self, critical_section_timeout_seconds: float) -> float:
        """返回临界区的绝对截止时间，必须严格早于租约到期。

        临界区跑过租约到期点时，锁其实已经可以被别人拿走，继续执行就失去了互斥意义，
        因此这里直接拒绝而不是让调用方带着失效的锁继续跑。
        """
        if not self._acquired or self._lease_deadline is None:
            raise CacheException(CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="锁实例尚未持有有效租约")
        critical_deadline = asyncio.get_running_loop().time() + critical_section_timeout_seconds
        if critical_deadline >= self._lease_deadline:
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="剩余租约不足以覆盖临界区执行上界"
            )
        return critical_deadline

    @staticmethod
    def _parse_release_outcome(result: object) -> LockReleaseOutcomeEnum:
        """校验 Lua 返回的终态编码。"""
        if isinstance(result, bytes):
            try:
                code = result.decode("utf-8")
            except UnicodeDecodeError as error:
                raise CacheException(
                    CacheErrorCodes.LOCK_RELEASE_FAILED,
                    msg="Redis 返回未知的锁释放结果",
                    cause=error,
                ) from error
        elif isinstance(result, str):
            code = result
        else:
            raise CacheException(
                CacheErrorCodes.LOCK_RELEASE_FAILED, msg="Redis 返回未知的锁释放结果"
            )
        outcome = LockReleaseOutcomeEnum.get_by_code(code)
        if outcome is None:
            raise CacheException(
                CacheErrorCodes.LOCK_RELEASE_FAILED, msg="Redis 返回未知的锁释放结果"
            )
        return outcome

    @staticmethod
    def _to_lease_milliseconds(lease_seconds: float) -> int:
        """换算成 Redis 可接受的正 64 位毫秒值，向上取整避免租约短于声明值。"""
        milliseconds = lease_seconds * 1000
        if not math.isfinite(milliseconds) or milliseconds > _MAX_LEASE_MILLISECONDS:
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg="lease_seconds 超出 Redis 租约范围"
            )
        return math.ceil(milliseconds)

    @staticmethod
    def validate_seconds(value: float, field_name: str, *, allow_zero: bool) -> float:
        """拒绝永久租约、无限等待和非有限数字。"""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg=f"{field_name} 必须是有限数字"
            )
        normalized = float(value)
        lower_bound_valid = normalized >= 0 if allow_zero else normalized > 0
        if not math.isfinite(normalized) or not lower_bound_valid:
            comparator = ">= 0" if allow_zero else "> 0"
            raise CacheException(
                CacheErrorCodes.LOCK_ACQUIRE_FAILED, msg=f"{field_name} 必须有限且 {comparator}"
            )
        return normalized
