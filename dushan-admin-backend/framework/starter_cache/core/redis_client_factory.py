from redis.asyncio import BlockingConnectionPool, ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.config.redis_client_settings import RedisClientSettings
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_di.decorators.components import framework


@framework
class RedisClientFactory:
    """按配置创建单机 Redis 连接池与客户端，并执行一次显式探活。

    客户端不做任何自动重试：缓存写入与失效都有确定的先后语义，
    驱动层静默重放命令会让调用方看到无法解释的中间状态。
    """

    @staticmethod
    def create_pool(settings: CacheSettings, client: RedisClientSettings) -> ConnectionPool:
        """创建该逻辑客户端独占的连接池，连接池由调用方负责关闭。

        使用有界等待连接池：max_connections 是资源上限而不是并发上限，
        瞬时并发高于连接数时应当排队等待，超过 pool_wait_timeout_seconds 才失败，
        否则一次正常流量高峰会直接变成大量"连接数过多"错误。
        """
        return BlockingConnectionPool(
            host=settings.host,
            port=settings.port,
            db=client.db,
            username=settings.username,
            password=None if settings.password is None else settings.password.get_secret_value(),
            decode_responses=True,
            max_connections=settings.max_connections,
            socket_timeout=settings.socket_timeout_seconds,
            socket_connect_timeout=settings.socket_connect_timeout_seconds,
            health_check_interval=settings.connection_health_check_seconds,
            timeout=settings.pool_wait_timeout_seconds,
            retry=Retry(NoBackoff(), 0),
        )

    @staticmethod
    def create_client(pool: ConnectionPool) -> Redis:
        """在已创建的连接池上构造客户端。"""
        return Redis(connection_pool=pool)

    @staticmethod
    async def require_ping(client: Redis) -> None:
        """探活必须明确返回成功，握手失败不允许当作可用连接继续启动。"""
        if not await client.ping():
            raise CacheException(CacheErrorCodes.CONNECTION_FAILED, msg="Redis PING 未返回成功")
