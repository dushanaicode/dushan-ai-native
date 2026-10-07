from collections.abc import Callable
from functools import wraps
from typing import Any

from framework.starter_cache.core.cache_invalidation_dispatcher import CacheInvalidationDispatcher
from framework.starter_cache.decorators.key_builder import KeyBuilder
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.model.cache_entry_invalidation_command import (
    CacheEntryInvalidationCommand,
)
from framework.starter_cache.model.cache_invalidation_command import CacheInvalidationCommand
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_prefix_invalidation_command import (
    CachePrefixInvalidationCommand,
)
from framework.starter_di.context.application_context import ApplicationContext


class CacheEvict:
    """在写方法成功返回后失效对应缓存。

    用法：

        @invalidate(SystemCacheKeyConstants.ROLE, key="id:{{role_id}}")
        async def update_role(self, role_id: int, ...) -> None: ...

    命令在调用业务方法之前就构造好，因为渲染键模板需要入参；业务抛异常时不执行失效。
    即使把本装饰器放在 @transactional 外层，方法加入上游 REQUIRED 事务时，
    返回也不代表最外层事务已经提交，缓存仍可能提前失效。
    数据库写入必须在事务内通过 SessionProvider.after_commit 登记
    CacheInvalidationDispatcher 的失效动作，确保最外层事务成功提交后才执行；
    本装饰器不替代提交后回调。
    """

    @classmethod
    def invalidate(cls, cache_key: CacheKey, *, key: str | None = None, all_entries: bool = False):
        """构造失效装饰器；key 与 all_entries 必须且只能指定一个。"""
        if not isinstance(cache_key, CacheKey):
            raise CacheException(
                CacheErrorCodes.INVALID_CACHE_KEY, msg="缓存失效装饰器必须传入 CacheKey"
            )
        if (key is not None) == all_entries:
            raise CacheException(
                CacheErrorCodes.CONFIG_ERROR,
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
                await ApplicationContext.lookup(CacheInvalidationDispatcher).dispatch(command)
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
