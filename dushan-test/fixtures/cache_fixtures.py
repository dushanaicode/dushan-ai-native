"""starter_cache 用例共用的真实实例配置与清理工具，按项目约定放在测试根目录。"""

import json
import os
from collections import namedtuple

import pytest

from fixtures.config_factory import ConfigFactory
from framework.starter_cache.config.cache_settings import CacheSettings

# 单个用例的操作句柄：已进入执行边界的 CacheHandler、本轮键声明模块和运行中的应用。
CacheCase = namedtuple("CacheCase", "cache keys app")

# 真实 Redis 连接由运行脚本注入；没有实例时整组用例跳过，不使用内存假实现。
REDIS_TARGET = json.loads(os.environ.get("DUSHAN_CACHE_TEST_REDIS", "null"))

requires_redis = pytest.mark.skipif(REDIS_TARGET is None, reason="需要真实 Redis 实例")

# 容器源码在临时模块里生成，保证键声明经过真实的模块扫描而不是测试内联构造。
KEY_CONTAINER_SOURCE = """
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_scanner.annotation.scanner_decorator import scanner


@scanner
class TestCacheKeys(CacheKeyContainer):
    ITEM = CacheKey(key="{prefix}:item", remark="测试条目", client_name="default")
    SHORT = CacheKey(
        key="{prefix}:short", remark="带默认过期的测试键", client_name="default",
        default_ttl_seconds=1,
    )
    SECOND = CacheKey(key="{prefix}:second", remark="第二个客户端", client_name="second")
"""


def redis_values(**overrides) -> dict:
    """按真实实例生成 cache 配置分组，用例只覆盖本场景关心的字段。"""
    values = ConfigFactory.values()["config"]["models"]["cache"]
    values.update(enabled=True, **(REDIS_TARGET or {}))
    values.update(overrides)
    return values


def cache_settings(**overrides) -> CacheSettings:
    """构造真实配置模型，供不需要完整应用的用例使用。"""
    return CacheSettings.model_validate(redis_values(**overrides))


def app_values(cache: dict, **extra) -> dict:
    """组装 create_app 需要的配置层，默认关闭横幅减少噪声。"""
    values = {"config": {"models": {"cache": cache}}, "banner": {"enabled": False}}
    values.update(extra)
    return values


async def clear_prefix(client, prefix: str) -> None:
    """只清理本用例前缀相关的键，不做 FLUSHDB，避免影响共享实例上的其他数据。"""
    keys = [key async for key in client.scan_iter(match=f"*{prefix}*", count=500)]
    if keys:
        await client.delete(*keys)


# DAO 子类必须经过真实扫描与容器装配，才能验证基类的注入字段在子类上生效。
DAO_SOURCE = """
from framework.starter_cache.repository.base_cache_dao import BaseCacheDAO
from framework.starter_di.decorators.components import dao

from {package}.keys import TestCacheKeys


@dao
class ItemCacheDAO(BaseCacheDAO):
    def __init__(self) -> None:
        super().__init__(TestCacheKeys.ITEM)
"""
