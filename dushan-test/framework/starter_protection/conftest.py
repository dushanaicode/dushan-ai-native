import asyncio
import json
import os
from contextlib import AsyncExitStack
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from fixtures.config_factory import ConfigFactory
from fixtures.public_web_app import create_public_app
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.core.redis_client_factory import RedisClientFactory
from framework.starter_protection.config.protection_settings import ProtectionSettings
from framework.starter_protection.core.protection_service import ProtectionService
from framework.starter_protection.subject.protection_subject import ProtectionSubject
from framework.starter_web.routing.router_registration import RouterRegistration

TARGET = json.loads(os.environ.get("DUSHAN_CACHE_TEST_REDIS", "null"))


@pytest.fixture
def namespace():
    return "ptest_" + uuid4().hex


@pytest.fixture
def subject():
    return ProtectionSubject(
        kind="principal", identifier="account-secret", realm="admin", tenant_id="tenant-one"
    )


@pytest.fixture
def settings(namespace):
    def build(**overrides):
        values = ConfigFactory.values()["config"]["models"]["protection"]
        values.update(enabled=True, key_prefix=namespace)
        ConfigFactory.merge(values, overrides)
        return ProtectionSettings.model_validate(values)

    return build


@pytest.fixture
async def services(settings):
    if TARGET is None:
        pytest.skip("需要 DUSHAN_CACHE_TEST_REDIS 指向独立真实 Redis")
    owned = []

    async def build(*, cache_overrides=None, observer=None, **overrides):
        options = settings(**overrides)
        values = ConfigFactory.values()["config"]["models"]["cache"]
        values.update(enabled=True, **TARGET)
        values.update(cache_overrides or {})
        cache_options = CacheSettings.model_validate(values)
        manager = CacheManager()
        manager._settings = cache_options
        manager._factory = RedisClientFactory()
        registry = CacheKeyRegistry()
        registry.register((), cache_options, resource_keys=(options.cache_key(),))
        cache = CacheHandler()
        cache._cache_manager = manager
        service = ProtectionService(options, cache)
        owned.append((service, manager))
        await manager.open()
        await service.open(observer=observer)
        return service

    yield build
    for service, manager in reversed(owned):
        try:
            await service.close()
            assert service.resources() == {
                "state": "closed",
                "active_operations": 0,
                "leases": 0,
                "closing_tasks": 0,
            }
            db = next(
                c.db for c in manager._settings.clients if c.name == service.settings.client_name
            )
            client = Redis(
                host=TARGET["host"],
                port=TARGET["port"],
                db=db,
                username=TARGET.get("username"),
                password=TARGET.get("password"),
            )
            try:
                keys = [
                    key async for key in client.scan_iter(match=f"{service.settings.key_prefix}:*")
                ]
                if keys:
                    await client.delete(*keys)
            finally:
                await client.aclose()
        finally:
            await manager.close()
            assert manager._active.is_empty and manager._pending_close.is_empty


@pytest.fixture
async def protection_app(config_dir, namespace):
    if TARGET is None:
        pytest.skip("需要真实 Redis")
    async with AsyncExitStack() as stack:

        async def build(*, overrides=None, prefix=None, routers=()):
            values = {
                "banner": {"enabled": False},
                "config": {
                    "models": {
                        "cache": {"enabled": True, **TARGET},
                        "protection": {"enabled": True, "key_prefix": prefix or namespace},
                    }
                },
            }
            ConfigFactory.merge(values, overrides or {})
            app = create_public_app(
                base_dir=config_dir(values),
                environ={},
                routers=[RouterRegistration(router) for router in routers],
            )
            await stack.enter_async_context(app.router.lifespan_context(app))
            return app

        yield build


class ResponseGate:
    """真实 TCP 转发，可在 Redis 已执行命令后扣住回包，重现结果未知与取消。"""

    def __init__(self):
        self.server = None
        self.tasks = set()
        self.freeze = False
        self.blocked = asyncio.Event()
        self.gate = asyncio.Event()
        self.gate.set()

    async def open(self):
        self.server = await asyncio.start_server(self.connect, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    def pause(self):
        self.freeze = True
        self.blocked.clear()
        self.gate.clear()

    def resume(self):
        self.freeze = False
        self.gate.set()

    async def connect(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        remote_writer = None
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                TARGET["host"], TARGET["port"]
            )
            async with asyncio.TaskGroup() as group:
                group.create_task(self.relay(reader, remote_writer, response=False))
                group.create_task(self.relay(remote_reader, writer, response=True))
        finally:
            for stream in (writer, remote_writer):
                if stream is not None:
                    stream.close()
                    await stream.wait_closed()
            self.tasks.discard(task)

    async def relay(self, reader, writer, *, response):
        while chunk := await reader.read(65536):
            if response and self.freeze:
                self.blocked.set()
                await self.gate.wait()
            writer.write(chunk)
            await writer.drain()
        writer.close()

    async def close(self):
        self.resume()
        self.server.close()
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.server.wait_closed()


@pytest.fixture
async def response_gate():
    if TARGET is None:
        pytest.skip("需要真实 Redis")
    proxy = await ResponseGate().open()
    try:
        yield proxy
    finally:
        await proxy.close()
