import json
import os
from uuid import uuid4

import pytest

from framework.starter_auth.config.configured_auth_clients import ConfiguredAuthClients
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.core.auth_service import AuthService
from framework.starter_auth.starter.auth_starter import AuthStarter
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.lock.distributed_lock import DistributedLock
from server.starter_server import create_app

from .support import client_config, settings


@pytest.fixture
async def harness(config_dir):
    target = json.loads(os.environ.get("DUSHAN_AUTH_TEST_REDIS", "null"))
    if target is None:
        pytest.skip("需要本轮私有 Redis；不以 mock 声称原子消费通过")
    values = {
        "banner": {"enabled": False},
        "config": {
            "models": {
                "cache": {
                    "enabled": True,
                    "host": target["host"],
                    "port": target["port"],
                    "clients": [{"name": "default", "db": 0}],
                }
            }
        },
    }
    app = create_app(base_dir=config_dir(values), environ={})
    starters = []
    namespaces = []
    async with app.router.lifespan_context(app):
        with app.state.application_context.execution():
            cache = app.state.application_context.get_bean(CacheHandler)
            locks = app.state.application_context.get_bean(DistributedLock)

            async def build(configs=None, transport=None, components=(), **overrides):
                namespace = "test-" + uuid4().hex
                config = settings(
                    clients=configs or (client_config(),), namespace=namespace, **overrides
                )
                namespaces.append(namespace)
                service = AuthService(
                    config, ConfiguredAuthClients(config), AuthProviderRegistry(), cache, locks
                )
                starter = AuthStarter(service)
                starters.append(starter)
                await starter.open(transport=transport, components=components)
                return service

            try:
                yield build, app, cache
            finally:
                for starter in starters:
                    await starter.close()
                client = app.state.cache.get_client("default")
                for namespace in namespaces:
                    keys = [key async for key in client.scan_iter(match=f"auth:*:{namespace}:*")]
                    if keys:
                        await client.delete(*keys)
