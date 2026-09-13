from collections.abc import Callable
from functools import wraps
from typing import Any

from framework.starter_cache.core.cache_invalidation_dispatcher import CacheInvalidationDispatcher
from framework.starter_cache.decorators.key_builder import KeyBuilder
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.model.cache_entry_invalidation_command import (
    CacheEntryInvalidationCommand,
)
from framework.starter_cache.model.cache_invalidation_command import CacheInvalidationCommand
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_prefix_invalidation_command import (
    CachePrefixInvalidationCommand,
)
from framework.starter_di.context.get_bean import get_bean


class CacheEvict:
    """在写方法成功返回后失效对应缓存。

    用法：

        @invalidate(SystemCacheKeys.ROLE, key="id:{{role_id}}")
        async def update_role(self, role_id: int, ...) -> None: ...

    命令在调用业务方法之前就构造好，因为渲染键模板需要入参；业务抛异常时不执行失效。
    涉及数据库事务时必须把本装饰器放在 @transactional 外层，
    否则失效会发生在提交之前，提交失败会留下已经被删掉的缓存和没有变化的数据。
    需要严格的"提交后再失效"语义时，改用 TransactionManager.after_commit 配合
    CacheInvalidationDispatcher，本装饰器不替代事务协作。
    """

    @classmethod
    def invalidate(cls, cache_key: CacheKey, *, key: str | None = None, all_entries: bool = False):
        """构造失效装饰器；key 与 all_entries 必须且只能指定一个。"""
        if not isinstance(cache_key, CacheKey):
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY, msg="缓存失效装饰器必须传入 CacheKey"
            )
        if (key is not None) == all_entries:
            raise CacheConfigException(
                error_code=CacheErrorCodes.CONFIG_ERROR,
                msg="缓存失效目标必须且只能指定 key 或 all_entries 之一",
            )

        def decorate(func: Callable[..., Any]):
            signature = KeyBuilder.validate_template(func, key)

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                command = cls._build_command(
                    cache_key, key, all_entries, func, signature, args, kwargs
                )
                result = await func(*args, **kwargs)
                await get_bean(CacheInvalidationDispatcher).dispatch(command)
                return result

            return wrapper

        return decorate

    @staticmethod
    def _build_command(
        cache_key: CacheKey,
        key: str | None,
        all_entries: bool,
        func: Callable[..., Any],
        signature,
        args: tuple,
        kwargs: dict,
    ) -> CacheInvalidationCommand:
        """按入参渲染出本次要执行的失效命令。"""
        if all_entries:
            return CachePrefixInvalidationCommand(cache_key=cache_key)
        return CacheEntryInvalidationCommand(
            cache_key=cache_key,
            identifier=KeyBuilder.build_identifier(key, func, signature, args, kwargs),
        )


invalidate = CacheEvict.invalidate
