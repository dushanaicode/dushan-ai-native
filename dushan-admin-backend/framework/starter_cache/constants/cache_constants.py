class CacheConstants:
    """跨缓存组件复用的稳定协议常量。

    这些值参与 Redis 中已写入数据的解析，修改会让在途的发布信封和 generation
    记录无法识别；调整时必须同时清理对应键或提升协议前缀版本。
    """

    # generation 栅栏键的固定命名空间，与业务 CacheKey 前缀不重叠。
    GENERATION_KEY_PREFIX = "cache_generation"
    GENERATION_GLOBAL_SCOPE = "global"
    GENERATION_PREFIX_SCOPE = "prefix"
    INITIAL_GENERATION_VERSION = 0

    # 发布信封的二进制前缀与 token 长度；token 是 generation 快照的 sha256 十六进制串。
    GENERATION_PUBLICATION_PREFIX = "__dushan_cache_generation_v1__:"
    GENERATION_TOKEN_LENGTH = 64
    GENERATION_TOKEN_SEPARATOR = ":"

    # 回源互斥锁与通用分布式锁各自独立的键前缀。
    LOAD_THROUGH_LOCK_PREFIX = "cache_lock"
    DISTRIBUTED_LOCK_KEY_PREFIX = "lock:"

    # 批量删除的单次 pipeline 规模，以及 SCAN 每轮返回的建议条数。
    DELETE_CHUNK_SIZE = 500
    SCAN_COUNT = 100
