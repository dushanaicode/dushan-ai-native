from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.model.cache_entry_invalidation_command import (
    CacheEntryInvalidationCommand,
)
from framework.starter_cache.model.cache_invalidation_command import CacheInvalidationCommand
from framework.starter_cache.model.cache_prefix_invalidation_command import (
    CachePrefixInvalidationCommand,
)
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject


@framework
class CacheInvalidationDispatcher:
    """执行一条已经构造好的缓存失效命令。

    命令与执行分开，是为了配合数据库事务：业务方法在事务内把命令构造好
    （此时参数还在手边），再交给 TransactionManager.after_commit 在提交后执行。
    这样回滚的事务不会误删缓存，提交后的失效也不会被回滚掩盖。
    """

    _cache_handler: CacheHandler = Inject()

    async def dispatch(self, command: CacheInvalidationCommand) -> int:
        """按命令类型执行失效，返回删除的键数量。"""
        if isinstance(command, CacheEntryInvalidationCommand):
            return await self._cache_handler.delete(command.cache_key, command.identifier)
        if isinstance(command, CachePrefixInvalidationCommand):
            return await self._cache_handler.delete_all(command.cache_key)
        raise CacheException(
            CacheErrorCodes.OPERATION_FAILED, msg=f"不支持的缓存失效命令：{type(command).__name__}"
        )
