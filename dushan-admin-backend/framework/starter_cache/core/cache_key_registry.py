from collections.abc import Iterable

from loguru import logger

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_di.decorators.components import framework


@framework
class CacheKeyRegistry:
    """汇总本应用声明的全部 CacheKey，并在启动时一次性校验键集合。

    运行期的读写直接传 CacheKey 对象，因此这里只负责部署期检查：前缀是否重复、
    是否互相包含、引用的客户端是否已配置、共置组是否落在同一个客户端。
    实例随应用容器创建，没有类级状态，两个应用的键集合互不影响。
    """

    def __init__(self) -> None:
        self._keys: dict[str, CacheKey] = {}
        self._registered = False

    @property
    def is_registered(self) -> bool:
        """启动流程是否已经完成一次键集合登记。"""
        return self._registered

    def register(
        self,
        containers: Iterable[type[CacheKeyContainer]],
        settings: CacheSettings,
        *,
        resource_keys: Iterable[CacheKey] = (),
    ) -> None:
        """统一校验静态声明和应用按配置解析的资源键；重复登记视为启动流程错误。"""
        if self._registered:
            raise CacheConfigException(msg="缓存键注册表不能重复登记")
        collected: dict[str, CacheKey] = {}
        for container in containers:
            for cache_key in container.declared_keys():
                self._collect(
                    collected, f"{container.__module__}.{container.__qualname__}", cache_key
                )
        for cache_key in resource_keys:
            self._collect(collected, "应用资源装配", cache_key)
        self._validate_clients(collected, settings)
        self._validate_colocation(collected)
        self._keys = collected
        self._registered = True
        logger.info("【CacheStarter 】缓存键登记完成：{} 个前缀", len(collected))

    @staticmethod
    def _collect(collected: dict[str, CacheKey], source: str, cache_key: CacheKey) -> None:
        """拒绝重复前缀，以及互为上下级的前缀。

        前缀 a 与 a:b 同时存在时，按 a 做整段失效会连带删除 a:b 的数据，
        归属和生命周期都会变得不可解释，因此在启动阶段直接失败。
        """
        if cache_key.key in collected:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=f"缓存键前缀重复声明：{cache_key.key}（{source}）",
            )
        overlapping = next(
            (
                existing
                for existing in collected
                if cache_key.key.startswith(f"{existing}:")
                or existing.startswith(f"{cache_key.key}:")
            ),
            None,
        )
        if overlapping is not None:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=f"缓存键前缀互相包含：{cache_key.key} <-> {overlapping}（{source}）",
            )
        collected[cache_key.key] = cache_key

    @staticmethod
    def _validate_clients(collected: dict[str, CacheKey], settings: CacheSettings) -> None:
        """键引用的客户端必须已经在配置中声明。"""
        configured = {client.name for client in settings.clients}
        missing = sorted(
            {
                cache_key.client_name
                for cache_key in collected.values()
                if cache_key.client_name not in configured
            }
        )
        if missing:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=f"缓存键引用了未配置的客户端：{', '.join(missing)}",
            )

    @staticmethod
    def _validate_colocation(collected: dict[str, CacheKey]) -> None:
        """同一共置组的前缀必须落在同一个客户端，否则跨 DB 的多键操作无法原子执行。"""
        groups: dict[str, list[CacheKey]] = {}
        for cache_key in collected.values():
            if cache_key.colocation_group is not None:
                groups.setdefault(cache_key.colocation_group, []).append(cache_key)
        for group, cache_keys in sorted(groups.items()):
            clients = {cache_key.client_name for cache_key in cache_keys}
            if len(clients) != 1:
                assignments = ", ".join(
                    f"{cache_key.key}={cache_key.client_name}"
                    for cache_key in sorted(cache_keys, key=lambda item: item.key)
                )
                raise CacheConfigException(
                    error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                    msg=f"缓存键共置组路由不一致：group={group}，{assignments}",
                )

    def get_all(self) -> dict[str, CacheKey]:
        """返回已登记键的副本，调用方修改结果不影响注册表。"""
        return dict(self._keys)

    def find(self, key: str) -> CacheKey | None:
        """按前缀查找已登记的 CacheKey，未登记返回 None。"""
        return self._keys.get(key)
