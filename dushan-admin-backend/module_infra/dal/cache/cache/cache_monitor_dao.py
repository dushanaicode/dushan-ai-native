import asyncio
import json
import re

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_di.public import (
    Inject,
    dao,
)
from module_infra.controller.admin.cache.vo.cache.cache_key_detail_resp_vo import (
    CacheKeyDetailRespVO,
)


@dao
class CacheMonitorDAO:
    manager: CacheManager = Inject()
    settings: CacheSettings = Inject()

    async def get_all_redis_clients(self):
        return {entry.name: self.manager.get_client(entry.name) for entry in self.settings.clients}

    async def get_redis_info(self):
        return await self.manager.get_default_client().info()

    async def get_db_size(self):
        return await self.manager.get_default_client().dbsize()

    async def get_command_stats(self):
        return await self.manager.get_default_client().info("commandstats")

    async def scan_keys(self, pattern, client_name="default"):
        return await self.scan_all_keys_in_db(client_name, pattern)

    async def get_value(self, key, client_name="default"):
        detail = await self.get_key_detail(client_name, key)
        return detail.value

    async def delete_keys(self, keys, client_name="default"):
        return await self.manager.get_client(client_name).unlink(*keys) if keys else 0

    async def flush_db(self, client_name="default"):
        return await self.manager.get_client(client_name).flushdb(asynchronous=True)

    async def get_all_client_stats(self):
        clients = await self.get_all_redis_clients()
        results = await asyncio.gather(
            *(self._get_client_stats(client) for client in clients.values())
        )
        return dict(zip(clients, results, strict=True))

    @staticmethod
    async def _get_client_stats(client):
        info, size = await asyncio.gather(client.info(), client.dbsize())
        return {"info": info, "dbsize": size}

    async def scan_all_keys_in_db(self, db_name, pattern="*", max_keys=5000):
        keys = []
        async for key in self.manager.get_client(db_name).scan_iter(match=pattern, count=200):
            keys.append(key.decode("utf-8"))
            if len(keys) >= max_keys:
                break
        return sorted(keys)

    async def get_key_detail(self, db_name, key):
        client = self.manager.get_client(db_name)
        kind = (await client.type(key)).decode("ascii")
        ttl = await client.ttl(key)
        if re.search(
            r"password|secret|credential|token|ticket|file_config|mail_account|sms_channel|social",
            key,
            re.I,
        ):
            value, size = "[redacted]", None
        else:
            value, size = await self._get_key_value_by_type(client, key, kind)
        return CacheKeyDetailRespVO(
            key=key, key_type=kind, ttl=ttl, db_name=db_name, value=value, size=size
        )

    async def delete_raw_key(self, db_name, key):
        return await self.manager.get_client(db_name).unlink(key)

    @staticmethod
    async def _get_key_value_by_type(client, key, kind):
        if kind == "none":
            return None, None
        if kind == "string":
            raw = await client.getrange(key, 0, 8191)
            return raw.decode("utf-8", errors="replace"), await client.strlen(key)
        if kind == "hash":
            _, entries = await client.hscan(key, count=100)
            data = {
                k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                for k, v in list(entries.items())[:100]
            }
            size = await client.hlen(key)
        elif kind == "list":
            data = [v.decode("utf-8", errors="replace") for v in await client.lrange(key, 0, 99)]
            size = await client.llen(key)
        elif kind == "set":
            _, entries = await client.sscan(key, count=100)
            data = [v.decode("utf-8", errors="replace") for v in entries[:100]]
            size = await client.scard(key)
        elif kind == "zset":
            data = [
                {"member": v.decode("utf-8", errors="replace"), "score": score}
                for v, score in await client.zrange(key, 0, 99, withscores=True)
            ]
            size = await client.zcard(key)
        elif kind == "stream":
            data = [
                {
                    "id": identifier.decode("ascii"),
                    "fields": list(v.decode("utf-8", errors="replace") for v in fields),
                }
                for identifier, fields in await client.xrange(key, count=100)
            ]
            size = await client.xlen(key)
        else:
            return "不支持的类型: " + kind, None
        return json.dumps(data, ensure_ascii=False), size
