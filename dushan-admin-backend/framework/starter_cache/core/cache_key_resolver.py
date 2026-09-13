from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.model.cache_key import CacheKey


class CacheKeyResolver:
    """把 CacheKey 与业务标识拼成 Redis 中的物理键。

    物理键固定是 "<前缀>:<标识>"。标识由调用方提供，可能来自请求参数，
    因此这里拒绝空串、首尾空白、换行和会被 SCAN 当成通配的字符，
    避免一次普通读写意外命中或删除同前缀下的其他数据。
    """

    # SCAN/KEYS 的 glob 元字符；出现在标识里会让精确操作变成模式匹配。
    _PATTERN_CHARACTERS = frozenset("*?[]\\")

    @classmethod
    def build_full_key(cls, cache_key: CacheKey, identifier: str) -> str:
        """构造一个确定标识的物理键。"""
        return f"{cache_key.key}:{cls._require_identifier(identifier)}"

    @staticmethod
    def build_prefix_pattern(cache_key: CacheKey) -> str:
        """构造该前缀下全部键的 SCAN 匹配模式。"""
        return f"{cache_key.key}:*"

    @staticmethod
    def build_prefix(cache_key: CacheKey) -> str:
        """返回不含分隔符的物理前缀，供 generation 栅栏键派生使用。"""
        return cache_key.key

    @classmethod
    def _require_identifier(cls, identifier: str) -> str:
        """标识必须是可安全拼接的普通字符串。"""
        if not isinstance(identifier, str) or not identifier:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY, msg="缓存标识不能为空"
            )
        if identifier != identifier.strip() or any(character.isspace() for character in identifier):
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY, msg="缓存标识不能包含空白字符"
            )
        if cls._PATTERN_CHARACTERS.intersection(identifier):
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg="缓存标识不能包含通配字符 * ? [ ] \\",
            )
        return identifier
