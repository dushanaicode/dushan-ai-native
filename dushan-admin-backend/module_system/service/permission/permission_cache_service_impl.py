from framework.starter_cache.public import CacheHandler
from framework.starter_database.public import (
    SessionProvider,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.service.permission.permission_cache_service import PermissionCacheService


@service(interface=PermissionCacheService)
class PermissionCacheServiceImpl(PermissionCacheService):
    """业务原子推进权限版本后登记缓存失效，提交失败时不会清缓存。"""

    cache: CacheHandler = Inject()
    database: SessionProvider = Inject()

    async def invalidate_role_caches(self) -> None:
        self._after_commit(
            (
                SystemCacheKeyConstants.USER_ROLE_ID_LIST,
                SystemCacheKeyConstants.MENU_ROLE_ID_LIST,
                SystemCacheKeyConstants.ROLE,
            )
        )

    async def invalidate_menu_caches(self) -> None:
        self._after_commit(
            (
                SystemCacheKeyConstants.MENU_ROLE_ID_LIST,
                SystemCacheKeyConstants.PERMISSION_MENU_ID_LIST,
                SystemCacheKeyConstants.USER_MENU_LIST,
            )
        )

    async def invalidate_user_caches(self) -> None:
        self._after_commit(
            (SystemCacheKeyConstants.USER_ROLE_ID_LIST, SystemCacheKeyConstants.USER_MENU_LIST)
        )

    async def invalidate_all(self) -> None:
        await self._invalidate(
            (
                SystemCacheKeyConstants.USER_ROLE_ID_LIST,
                SystemCacheKeyConstants.MENU_ROLE_ID_LIST,
                SystemCacheKeyConstants.PERMISSION_MENU_ID_LIST,
                SystemCacheKeyConstants.USER_MENU_LIST,
                SystemCacheKeyConstants.ROLE,
                SystemCacheKeyConstants.DEPT_CHILDREN_ID_LIST,
            )
        )

    def _after_commit(self, keys):
        self.database.after_commit(
            lambda: self._invalidate(keys), required=True, name="system-permissions"
        )

    async def _invalidate(self, keys):
        for key in keys:
            await self.cache.delete_all(key)
