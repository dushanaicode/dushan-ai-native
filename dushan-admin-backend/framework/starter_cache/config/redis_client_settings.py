from pydantic import Field

from framework.starter_config.config.config_model import ConfigModel


class RedisClientSettings(ConfigModel):
    """一个具名 Redis 逻辑客户端；CacheKey 通过 name 选择自己所属的连接和 DB。"""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    db: int = Field(ge=0, le=15)
