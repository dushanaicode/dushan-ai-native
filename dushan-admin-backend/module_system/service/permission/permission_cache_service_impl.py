from framework.starter_cache.public import CacheHandler
from framework.starter_database.public import (
    SessionProvider,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.service.permission.permission_cache_service import PermissionCacheService


@service(interface=PermissionCacheService)
class PermissionCacheServiceImpl(PermissionCacheService):
    """业务原子推进权限版本后登记缓存失效，提交失败时不会清缓存。"""

    cache: CacheHandler = Inject()
    database: SessionProvider = Inject()

    async def invalidate_role_caches(self) -> None:
        self._after_commit(
            (
                SystemCacheKeys.USER_ROLE_ID_LIST,
                SystemCacheKeys.MENU_ROLE_ID_LIST,
                SystemCacheKeys.ROLE,
            )
        )

    async def invalidate_menu_caches(self) -> None:
        self._after_commit(
            (
                SystemCacheKeys.MENU_ROLE_ID_LIST,
                SystemCacheKeys.PERMISSION_MENU_ID_LIST,
                SystemCacheKeys.USER_MENU_LIST,
            )
        )

    async def invalidate_user_caches(self) -> None:
        self._after_commit((SystemCacheKeys.USER_ROLE_ID_LIST, SystemCacheKeys.USER_MENU_LIST))

    async def invalidate_all(self) -> None:
        await self._invalidate(
            (
                SystemCacheKeys.USER_ROLE_ID_LIST,
                SystemCacheKeys.MENU_ROLE_ID_LIST,
                SystemCacheKeys.PERMISSION_MENU_ID_LIST,
                SystemCacheKeys.USER_MENU_LIST,
                SystemCacheKeys.ROLE,
                SystemCacheKeys.DEPT_CHILDREN_ID_LIST,
            )
        )

    def _after_commit(self, keys):
        self.database.after_commit(
            lambda: self._invalidate(keys), required=True, name="system-permissions"
        )

    async def _invalidate(self, keys):
        for key in keys:
            await self.cache.delete_all(key)
