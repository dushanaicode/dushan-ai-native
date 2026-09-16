import pytest

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.enums.cache_namespace import CacheNamespace
from framework.starter_cache.enums.lock_release_outcome_enum import LockReleaseOutcomeEnum
from framework.starter_cache.lock.redis_lease_lock import RedisLeaseLock
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_tenant.exception.tenant_exception import TenantException


@pytest.mark.parametrize("tenant_case", [{"cache": True}], indirect=True)
async def test_real_redis_namespace_prefix_deletion_and_locks(tenant_case):
    case = tenant_case
    with case.app.state.application_context.execution():
        cache = case.app.state.application_context.container.get(CacheHandler)
    key = CacheKey(
        key="tenant_scope_test",
        remark="租户隔离验证",
        client_name="default",
        namespace=CacheNamespace.TENANT,
    )
    global_key = CacheKey(key="global_scope_test", remark="全局隔离验证", client_name="default")
    one, _ = case.issue(tenant="1")
    two, _ = case.issue(tenant="2")
    with case.app.state.application_context.execution():
        await cache.set(global_key, "same", "global", 30)
        with pytest.raises(TenantException):
            await cache.get(key, "same")
    keys = []
    for token, value in ((one, "one"), (two, "two")):
        async with case.enter(token):
            keys.append(cache.build_full_key(key, "same"))
            await cache.set(key, "same", value, 30)
    assert keys[0] != keys[1]
    async with case.enter(one):
        assert (await cache.get(key, "same")).value == "one"
        snapshot = await cache.capture_generation(key)
        first_lock = RedisLeaseLock(cache.get_client(key), cache.build_full_key(key, "lock"), 5, 0)
        assert await first_lock.acquire()
        try:
            async with case.enter(two):
                second_lock = RedisLeaseLock(
                    cache.get_client(key), cache.build_full_key(key, "lock"), 5, 0
                )
                assert await second_lock.acquire()
                assert await second_lock.release() is LockReleaseOutcomeEnum.RELEASED
                await cache.delete_all(key)
                await cache.set(key, "same", "two", 30)
            assert await cache.publish_loaded_value(key, "fresh", "one", snapshot, 30)
        finally:
            assert await first_lock.release() is LockReleaseOutcomeEnum.RELEASED
        assert await cache.delete_all(key) == 2
    async with case.enter(two):
        assert (await cache.get(key, "same")).value == "two"
        await cache.delete_all(key)
    with case.app.state.application_context.execution():
        assert (await cache.get(global_key, "same")).value == "global"
        await cache.delete_all(global_key)
