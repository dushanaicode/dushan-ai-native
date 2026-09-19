from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from framework.common.schemas.base_bo import BaseBO
from framework.starter_cache.definitions.enums.cache_namespace import CacheNamespace

# 键前缀只允许小写字母、数字、下划线，冒号用于分段；物理键为 "<key>:<identifier>"。
type CacheKeyName = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)*$", max_length=128),
]
type CacheKeyText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=255)
]
type CacheClientName = Annotated[
    str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,62}$")
]


class CacheKey(BaseBO):
    """一段缓存键前缀的权威声明：归属哪个 Redis 客户端、默认存活多久、用途是什么。

    业务模块把 CacheKey 常量写在 CacheKeyContainer 子类里，读写和失效都直接传这个对象，
    因此运行期不需要按字符串反查注册表，也不会出现前缀与客户端不一致的调用。
    colocation_group 声明必须落在同一个客户端的一组前缀，启动时统一校验。
    """

    model_config = ConfigDict(frozen=True)

    key: CacheKeyName
    remark: CacheKeyText
    client_name: CacheClientName
    namespace: CacheNamespace = CacheNamespace.GLOBAL
    default_ttl_seconds: int | None = Field(default=None, strict=True, gt=0)
    colocation_group: CacheKeyText | None = None
