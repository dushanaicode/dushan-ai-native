import hashlib
import json

from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_mq.exception.mq_exception import MQException


class ReplayStore:
    """复用 Cache 租约；运行、待结算及完成状态覆盖整个签名有效期。"""

    def __init__(self, client, prefix, settings):
        self.client, self.prefix, self.settings = client, prefix, settings

    def key(self, definition, envelope, *, instance):
        # 可丢广播每个在线实例独立去重，不能把广播收敛成竞争消费。
        identity = [
            definition.destination,
            definition.key,
            envelope.tenant_id,
            envelope.message_id,
            instance,
        ]
        return self.prefix + ":claim:" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def lock(self, key):
        return RedisLeaseLock(
            self.client,
            key + ":lock",
            self.settings.lease_seconds,
            0,
            command_timeout_seconds=self.settings.command_timeout_seconds,
        )

    async def read(self, key):
        raw = await self.client.get(key)
        return None if raw is None else json.loads(raw)

    async def write(self, key, lock, values):
        if not lock.is_valid:
            raise MQException("lease")
        result = await self.client.eval(
            "if redis.call('GET',KEYS[1]) ~= ARGV[1] then return 0 end "
            "redis.call('SET',KEYS[2],ARGV[2],'EX',ARGV[3]); return 1",
            2,
            lock.key,
            key,
            lock.owner_token,
            json.dumps(values, separators=(",", ":")),
            self.settings.replay_retention_seconds,
        )
        if result != 1:
            raise MQException("lease")
