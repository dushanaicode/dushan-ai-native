import json
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

from pydantic import TypeAdapter, ValidationError

from framework.starter_cache.constants.cache_lock_defaults import CacheLockDefaults
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_load_through_coordinator import CacheLoadThroughCoordinator
from framework.starter_cache.decorators.key_builder import KeyBuilder
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_serialization_exception import (
    CacheSerializationException,
)
from framework.starter_cache.lock.distributed_lock import DistributedLock
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_read_result import CacheReadResult
from framework.starter_di.context.get_bean import get_bean


class Cacheable:
    """给异步查询方法加上读缓存与回源的装饰器。

    用法：

        @cache(SystemCacheKeys.ROLE, key="id:{{role_id}}", ttl_seconds=3600)
        async def get_role(self, role_id: int) -> RoleDO | None: ...

    被装饰函数必须声明可解析的返回类型：缓存里存的是 JSON，读回后要按声明的类型
    重新校验，否则调用方会拿到 dict 而不是模型对象。只有来自缓存的值才做这次校验，
    刚回源得到的对象原样返回。校验失败按缓存内容损坏处理，删除后重新回源。

    组件每次调用都通过 get_bean 从当前应用解析，绝不在类上缓存实例；
    否则第一个应用创建的 CacheHandler 会被之后所有应用共用，跨应用串数据。
    """

    @classmethod
    def cache(
        cls,
        cache_key: CacheKey,
        *,
        key: str | None = None,
        ttl_seconds: int | None = None,
        unless: Callable[..., bool] | None = None,
        use_lock: bool = True,
        lease_seconds: float = CacheLockDefaults.LEASE_SECONDS,
        wait_seconds: float = CacheLockDefaults.WAIT_SECONDS,
        critical_section_timeout_seconds: float = CacheLockDefaults.CRITICAL_SECTION_TIMEOUT_SECONDS,
    ):
        """构造装饰器；TTL、锁时序和键模板都在装饰阶段完成校验。"""
        if not isinstance(cache_key, CacheKey):
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY, msg="缓存装饰器必须传入 CacheKey"
            )
        cls._validate_ttl(ttl_seconds)
        if unless is not None and not callable(unless):
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR, msg="unless 必须是可调用对象"
            )
        if use_lock:
            DistributedLock.validate_timing(
                lease_seconds, wait_seconds, critical_section_timeout_seconds
            )

        def decorate(func: Callable[..., Any]):
            signature = KeyBuilder.validate_template(func, key)
            adapter = cls._build_return_adapter(func)

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                identifier = KeyBuilder.build_identifier(key, func, signature, args, kwargs)
                handler = get_bean(CacheHandler)
                return await get_bean(CacheLoadThroughCoordinator).get_or_load(
                    full_key=handler.build_full_key(cache_key, identifier),
                    read=lambda: cls._read_validated(handler, cache_key, identifier, adapter),
                    delete_corrupted=lambda: handler.delete(cache_key, identifier),
                    load_and_publish=lambda: cls._load_and_publish(
                        handler, cache_key, identifier, ttl_seconds, unless, func, args, kwargs
                    ),
                    client_name=cache_key.client_name,
                    use_lock=use_lock,
                    lease_seconds=lease_seconds,
                    wait_seconds=wait_seconds,
                    critical_section_timeout_seconds=critical_section_timeout_seconds,
                )

            return wrapper

        return decorate

    @classmethod
    async def _read_validated(
        cls, handler: CacheHandler, cache_key: CacheKey, identifier: str, adapter: TypeAdapter
    ) -> CacheReadResult[Any]:
        """读缓存并按声明的返回类型还原。"""
        result = await handler.get(cache_key, identifier)
        if not result.hit:
            return CacheReadResult[Any](hit=False)
        return CacheReadResult[Any](
            hit=True, value=cls._validate_cached_value(result.value, adapter)
        )

    @classmethod
    async def _load_and_publish(
        cls,
        handler: CacheHandler,
        cache_key: CacheKey,
        identifier: str,
        ttl_seconds: int | None,
        unless: Callable[..., bool] | None,
        func: Callable[..., Any],
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """先记录 generation 再回源，unless 判定不缓存时只返回结果不写入。"""
        snapshot = await handler.capture_generation(cache_key)
        value = await func(*args, **kwargs)
        if unless is not None and unless(value, *args, **kwargs):
            return value
        await handler.publish_loaded_value(cache_key, identifier, value, snapshot, ttl_seconds)
        return value

    @staticmethod
    def _validate_cached_value(value: Any, adapter: TypeAdapter) -> Any:
        """把 JSON 形态的缓存值按声明类型还原；不匹配视为缓存内容损坏。"""
        try:
            payload = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            return adapter.validate_json(payload)
        except (ValidationError, TypeError, ValueError) as error:
            raise CacheSerializationException(
                error_code=CacheErrorCodes.DESERIALIZATION_FAILED,
                msg="缓存值不符合被装饰函数声明的返回类型",
                cause=error,
            ) from error

    @staticmethod
    def _build_return_adapter(func: Callable[..., Any]) -> TypeAdapter:
        """在装饰阶段冻结返回值边界，避免上线后才发现类型无法解析。"""
        try:
            return TypeAdapter(get_type_hints(func, include_extras=True)["return"])
        except (KeyError, NameError, TypeError, ValueError) as error:
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR,
                msg=f"缓存函数必须声明可解析的返回类型：{func.__qualname__}",
                cause=error,
            ) from error

    @staticmethod
    def _validate_ttl(ttl_seconds: int | None) -> None:
        """TTL 只接受正整数秒或 None。"""
        if ttl_seconds is not None and (type(ttl_seconds) is not int or ttl_seconds <= 0):
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR, msg="缓存 TTL 必须是正整数秒或 None"
            )


cache = Cacheable.cache
