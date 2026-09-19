import time

from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.definitions.enums.socket_target_kind import SocketTargetKind
from framework.starter_websocket.exception.websocket_exception import WebSocketException
from framework.starter_websocket.model.online_connection import OnlineConnection


class OnlineRegistry:
    """实例租约过滤在线连接；只删除当前实例、当前连接自己的记录。"""

    def __init__(self, runtime, client, prefix):
        self.runtime, self.client, self.prefix = runtime, client, prefix
        self.deadline = 0.0
        self.instance_key = prefix + ":instance:" + runtime.instance
        self.connections_key = prefix + ":connections:" + runtime.instance
        self.instances_key = prefix + ":instances"

    async def open(self):
        started = time.monotonic()
        milliseconds = int(self.runtime.settings.instance_lease_seconds * 1000)
        accepted = await self.client.set(
            self.instance_key, self.runtime.instance, nx=True, px=milliseconds
        )
        if not accepted:
            raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)
        await self.client.zadd(
            self.instances_key,
            {self.runtime.instance: time.time() + self.runtime.settings.instance_lease_seconds},
        )
        self.deadline = started + self.runtime.settings.instance_lease_seconds

    @property
    def valid(self):
        return time.monotonic() < self.deadline

    async def renew(self):
        if not self.valid:
            raise WebSocketException(WebSocketErrorCodes.TRANSPORT)
        settings = self.runtime.settings
        started = time.monotonic()
        result = await self.client.eval(
            "if redis.call('GET',KEYS[1])~=ARGV[1] then return 0 end "
            "redis.call('PEXPIRE',KEYS[1],ARGV[2]); redis.call('PEXPIRE',KEYS[2],ARGV[2]); "
            "redis.call('ZADD',KEYS[3],ARGV[3],ARGV[1]); "
            "redis.call('ZREMRANGEBYSCORE',KEYS[3],'-inf',ARGV[4]); return 1",
            3,
            self.instance_key,
            self.connections_key,
            self.instances_key,
            self.runtime.instance,
            int(settings.instance_lease_seconds * 1000),
            time.time() + settings.instance_lease_seconds,
            time.time(),
        )
        if result != 1:
            self.deadline = 0.0
            raise WebSocketException(WebSocketErrorCodes.TRANSPORT)
        self.deadline = started + settings.instance_lease_seconds

    async def add(self, connection):
        result = await self.client.eval(
            "if redis.call('GET',KEYS[1])~=ARGV[1] then return 0 end "
            "redis.call('HSET',KEYS[2],ARGV[2],ARGV[3]); redis.call('PEXPIRE',KEYS[2],ARGV[4]); return 1",
            2,
            self.instance_key,
            self.connections_key,
            self.runtime.instance,
            connection.client_id,
            connection.model_dump_json(),
            int(self.runtime.settings.instance_lease_seconds * 1000),
        )
        if result != 1:
            raise WebSocketException(WebSocketErrorCodes.TRANSPORT)

    async def remove(self, connection):
        await self.client.eval(
            "if redis.call('GET',KEYS[1])~=ARGV[1] then return 0 end "
            "return redis.call('HDEL',KEYS[2],ARGV[2])",
            2,
            self.instance_key,
            self.connections_key,
            self.runtime.instance,
            connection.client_id,
        )

    async def query(self, target):
        now = time.time()
        await self.client.zremrangebyscore(self.instances_key, "-inf", now)
        instances = await self.client.zrangebyscore(
            self.instances_key,
            now,
            "+inf",
            start=0,
            num=self.runtime.settings.online_query_limit + 1,
        )
        if len(instances) > self.runtime.settings.online_query_limit:
            raise WebSocketException(WebSocketErrorCodes.CAPACITY)
        result = []
        for instance in instances:
            raw = await self.client.eval(
                "if not redis.call('GET',KEYS[1]) then return {} end "
                "if redis.call('HLEN',KEYS[2])>tonumber(ARGV[1]) then return false end "
                "return redis.call('HVALS',KEYS[2])",
                2,
                self.prefix + ":instance:" + instance,
                self.prefix + ":connections:" + instance,
                self.runtime.settings.max_connections,
            )
            if raw is None:
                raise WebSocketException(WebSocketErrorCodes.CAPACITY)
            for item in raw:
                if len(item.encode()) > 4096:
                    raise WebSocketException(WebSocketErrorCodes.PROTOCOL)
                connection = OnlineConnection.model_validate_json(item)
                if connection.instance != instance:
                    raise WebSocketException(WebSocketErrorCodes.PROTOCOL)
                if self.matches(connection, target):
                    result.append(connection)
                if len(result) > self.runtime.settings.online_query_limit:
                    raise WebSocketException(WebSocketErrorCodes.CAPACITY)
        return tuple(result)

    @staticmethod
    def matches(connection, target):
        if connection.audience != target.audience:
            return False
        if target.kind is SocketTargetKind.AUDIENCE:
            return True
        if connection.tenant_id != target.tenant_id:
            return False
        if target.kind is SocketTargetKind.CLIENT:
            return connection.client_id == target.client_id
        if target.kind is SocketTargetKind.MEMBER:
            return connection.member_id == target.member_id
        return True

    async def close(self):
        self.deadline = 0.0
        await self.client.eval(
            "if redis.call('GET',KEYS[1])~=ARGV[1] then return 0 end "
            "redis.call('DEL',KEYS[1],KEYS[2]); redis.call('ZREM',KEYS[3],ARGV[1]); return 1",
            3,
            self.instance_key,
            self.connections_key,
            self.instances_key,
            self.runtime.instance,
        )
