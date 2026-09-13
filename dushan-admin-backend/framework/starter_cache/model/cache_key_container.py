from framework.starter_cache.model.cache_key import CacheKey


class CacheKeyContainer:
    """业务模块声明缓存键的容器基类；子类把 CacheKey 常量写成类属性。

    用法：

        @framework(providers=[CacheKeyContainer])
        class SystemCacheKeys(CacheKeyContainer):
            ROLE = CacheKey(key="role", remark="角色信息", client_name="default")

    容器由 DI 以 list[CacheKeyContainer] 汇总，CacheKeyRegistry 在启动时统一校验键集合；
    容器本身不持有连接，也不在导入时注册任何全局状态。
    """

    @classmethod
    def declared_keys(cls) -> tuple[CacheKey, ...]:
        """按名称顺序返回本容器及其基类声明的全部 CacheKey。"""
        declared: dict[str, CacheKey] = {}
        for owner in reversed(cls.__mro__):
            for name, value in vars(owner).items():
                if isinstance(value, CacheKey):
                    declared[name] = value
        return tuple(declared[name] for name in sorted(declared))
