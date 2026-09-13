from dataclasses import dataclass, field

from redis.asyncio import ConnectionPool, Redis


@dataclass(slots=True)
class CacheResourceSnapshot:
    """一代 Redis 连接资源的唯一所有权快照。

    连接池先登记、客户端后登记，关闭时逆序释放；这样探活失败或启动被取消时，
    已经创建的连接仍然有明确归属，不会留下没人回收的 socket。
    """

    clients: dict[str, Redis] = field(default_factory=dict)
    pools: dict[str, ConnectionPool] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """快照中没有任何待释放资源时返回 True。"""
        return not self.clients and not self.pools

    def merge(self, other: "CacheResourceSnapshot") -> "CacheResourceSnapshot":
        """合并两代资源用于统一关闭，不修改任何一方。"""
        return CacheResourceSnapshot(
            clients={**self.clients, **other.clients},
            pools={**self.pools, **other.pools},
        )
