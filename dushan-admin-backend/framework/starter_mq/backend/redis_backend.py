import asyncio
import hashlib
import time
from uuid import uuid4

from redis.exceptions import ResponseError

from framework.starter_mq.backend.message_backend import MessageBackend
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.delivery import Delivery


class RedisBackend(MessageBackend):
    """复用 Cache 连接，使用原生消费组/XAUTOCLAIM，不再叠加 PEL 心跳租约。"""

    _ADD = """
local cap = tonumber(ARGV[2])
if redis.call('XLEN',KEYS[1]) >= cap then
  local groups = redis.call('XINFO','GROUPS',KEYS[1])
  local boundary = nil
  local function field(t,k) for i=1,#t,2 do if t[i]==k then return t[i+1] end end end
  local function less(a,b)
    local am,as = string.match(a,'(%d+)%-(%d+)')
    local bm,bs = string.match(b,'(%d+)%-(%d+)')
    return tonumber(am)<tonumber(bm) or (am==bm and tonumber(as)<tonumber(bs))
  end
  for _,g in ipairs(groups) do
    local last=field(g,'last-delivered-id')
    local p=redis.call('XPENDING',KEYS[1],field(g,'name'))
    local current=p[2]
    if tonumber(p[1])==0 then
      local ms,seq=string.match(last,'(%d+)%-(%d+)')
      current=ms..'-'..tostring(tonumber(seq)+1)
    end
    if not boundary or less(current,boundary) then boundary=current end
  end
  if boundary then redis.call('XTRIM',KEYS[1],'MINID','=',boundary) end
end
if redis.call('XLEN',KEYS[1]) >= cap then return false end
return redis.call('XADD',KEYS[1],'*','body',ARGV[1])
"""
    _RETRY = """
if redis.call('ZSCORE',KEYS[1],ARGV[1]) then return 1 end
if redis.call('ZCARD',KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('ZADD',KEYS[1],ARGV[2],ARGV[1]); return 1
"""
    _PROMOTE = """
local items=redis.call('ZRANGEBYSCORE',KEYS[1],'-inf',ARGV[1],'LIMIT',0,ARGV[2])
local n=0
for _,body in ipairs(items) do
  if redis.call('XLEN',KEYS[2]) >= tonumber(ARGV[3]) then break end
  redis.call('XADD',KEYS[2],'*','body',body)
  redis.call('ZREM',KEYS[1],body); n=n+1
end
return n
"""
    _DELETE_IDLE = """
local c=redis.call('XINFO','CONSUMERS',KEYS[1],ARGV[1])
for _,item in ipairs(c) do
  local name=nil; local pending=0; local idle=0
  for i=1,#item,2 do
    if item[i]=='name' then name=item[i+1] end
    if item[i]=='pending' then pending=tonumber(item[i+1]) end
    if item[i]=='idle' then idle=tonumber(item[i+1]) end
  end
  if pending==0 and (name==ARGV[2] or idle>tonumber(ARGV[3])) then
    redis.call('XGROUP','DELCONSUMER',KEYS[1],ARGV[1],name)
  end
end
return 1
"""

    def __init__(self, client, prefix, settings):
        self.client, self.prefix, self.settings = client, prefix, settings
        self.receiving = False
        self.subscriptions = []
        self.bindings = []
        self.ready = {}

    def stream(self, destination):
        return self.prefix + ":stream:" + destination

    def channel(self, destination):
        return self.prefix + ":pubsub:" + destination

    def retry_stream(self, definition):
        return self.prefix + ":retry:" + definition.key

    def delay_key(self, definition):
        return self.prefix + ":delay:" + definition.key

    def dlq(self, definition):
        return self.prefix + ":dlq:" + definition.key

    async def open(self, definitions):
        self.ready = {definition.key: asyncio.Event() for definition in definitions}
        await self.client.ping()
        for definition in definitions:
            if definition.mode is MessageMode.STREAM:
                for key in (self.stream(definition.destination), self.retry_stream(definition)):
                    try:
                        await self.client.xgroup_create(
                            key, definition.group, id="0-0", mkstream=True
                        )
                    except ResponseError as error:
                        if not str(error).startswith("BUSYGROUP "):
                            raise
        self.receiving = True

    async def publish(self, destination, mode, body):
        if mode is MessageMode.PUBSUB:
            count = await self.client.publish(self.channel(destination), body)
            return "broadcast", str(count)
        entry = await self.client.eval(
            self._ADD, 1, self.stream(destination), body, self.settings.stream_max_length
        )
        if entry is None:
            raise MQException(MQErrorCodes.CAPACITY)
        return "stream_entry", entry

    async def retry(self, definition, envelope, body):
        accepted = await self.client.eval(
            self._RETRY,
            1,
            self.delay_key(definition),
            body,
            envelope.ready_at,
            self.settings.retry_max_length,
        )
        if accepted != 1:
            raise MQException(MQErrorCodes.CAPACITY)

    async def dead_letter(self, definition, body):
        key = self.dlq(definition)
        digest = hashlib.sha256(body).hexdigest()
        entry = await self.client.eval(
            "local old=redis.call('GET',KEYS[2]); if old then return old end "
            "local now=redis.call('TIME'); local cut=(tonumber(now[1])-tonumber(ARGV[3]))*1000; "
            "redis.call('XTRIM',KEYS[1],'MINID','=',tostring(math.max(0,cut))..'-0'); "
            "local id=redis.call('XADD',KEYS[1],'MAXLEN','=',ARGV[2],'*','body',ARGV[1]); "
            "redis.call('SET',KEYS[2],id,'EX',ARGV[3]); redis.call('EXPIRE',KEYS[1],ARGV[3]); return id",
            2,
            key,
            key + ":dedupe:" + digest,
            body,
            self.settings.dead_letter_max_length,
            self.settings.dead_letter_retention_seconds,
        )
        if not entry:
            raise MQException(MQErrorCodes.CONFIRMATION)

    def messages(self, definition, prefetch):
        return (
            self._pubsub(definition)
            if definition.mode is MessageMode.PUBSUB
            else self._stream(definition, prefetch)
        )

    async def _pubsub(self, definition):
        subscription = self.client.pubsub(ignore_subscribe_messages=False)
        self.subscriptions.append(subscription)
        await subscription.subscribe(self.channel(definition.destination))
        confirmation = await subscription.get_message(timeout=self.settings.command_timeout_seconds)
        if confirmation is None or confirmation["type"] != "subscribe":
            raise MQException(MQErrorCodes.CONFIRMATION)
        subscription.ignore_subscribe_messages = True
        self.ready[definition.key].set()
        try:
            while self.receiving:
                item = await subscription.get_message(timeout=self.settings.poll_seconds)
                if item is not None:
                    yield Delivery(
                        item["data"].encode(), "pubsub", False, self._no_ack, self._no_ack
                    )
        finally:
            await subscription.aclose()
            self.subscriptions.remove(subscription)

    @staticmethod
    async def _no_ack():
        # Pub/Sub 没有传输确认；注册阶段已拒绝可靠性声明。
        return None

    async def _stream(self, definition, prefetch):
        owner = uuid4().hex
        keys = (self.stream(definition.destination), self.retry_stream(definition))
        self.bindings.append((keys, definition.group, owner))
        self.ready[definition.key].set()
        cursors = {key: "0-0" for key in keys}
        reclaim_at = 0.0
        while self.receiving:
            await self.client.eval(
                self._PROMOTE,
                2,
                self.delay_key(definition),
                keys[1],
                time.time(),
                prefetch,
                self.settings.retry_max_length,
            )
            now = asyncio.get_running_loop().time()
            if now >= reclaim_at:
                reclaim_at = now + self.settings.poll_seconds
                for key in keys:
                    claimed = await self.client.xautoclaim(
                        key,
                        definition.group,
                        owner,
                        int(self.settings.lease_seconds * 1000),
                        start_id=cursors[key],
                        count=1,
                    )
                    cursors[key] = claimed[0]
                    for entry, fields in claimed[1]:
                        yield self._delivery(definition, owner, key, keys[1], entry, fields)
            batches = await self.client.xreadgroup(
                definition.group,
                owner,
                streams={key: ">" for key in keys},
                count=1,
                block=max(1, int(self.settings.poll_seconds * 1000)),
            )
            for raw_key, entries in batches:
                key = raw_key
                for entry, fields in entries:
                    yield self._delivery(definition, owner, key, keys[1], entry, fields)

    def _delivery(self, definition, owner, key, retry_key, entry, fields):
        async def acknowledge():
            if key == retry_key:
                await self.client.eval(
                    "redis.call('XACK',KEYS[1],ARGV[1],ARGV[2]); return redis.call('XDEL',KEYS[1],ARGV[2])",
                    1,
                    key,
                    definition.group,
                    entry,
                )
            else:
                await self.client.xack(key, definition.group, entry)

        async def release():
            # 保留 PEL；冷却后由 XAUTOCLAIM 接管，不热循环重投。
            await self.client.xclaim(key, definition.group, owner, 0, [entry], idle=0, justid=True)

        return Delivery(fields["body"].encode(), entry, key == retry_key, acknowledge, release)

    async def stop_receiving(self):
        self.receiving = False

    async def close(self):
        self.receiving = False
        for subscription in tuple(self.subscriptions):
            await subscription.aclose()
        self.subscriptions.clear()
        for keys, group, owner in self.bindings:
            for key in keys:
                await self.client.eval(
                    self._DELETE_IDLE, 1, key, group, owner, int(self.settings.lease_seconds * 2000)
                )
        self.bindings.clear()
        # Cache 是连接所有者，MQ 不关闭共享 Redis pool。
