from pydantic import Field, SecretStr, model_validator

from framework.starter_cache.config.redis_client_settings import RedisClientSettings
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "cache",
    env_prefix="CACHE_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class CacheSettings(ConfigModel):
    """启动期 Redis 契约；本轮只支持单机部署，哨兵与集群不在当前范围。

    clients 是本应用会建立的全部逻辑客户端，CacheKey 只能引用其中的 name；
    关闭 enabled 时不导入驱动、不建立连接，缓存组件也不会进入容器。
    """

    enabled: bool
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    username: str | None
    password: SecretStr | None
    clients: tuple[RedisClientSettings, ...]
    default_client: str
    max_connections: int = Field(gt=0)
    pool_wait_timeout_seconds: float = Field(gt=0)
    socket_timeout_seconds: float = Field(gt=0)
    socket_connect_timeout_seconds: float = Field(gt=0)
    connection_health_check_seconds: float = Field(ge=0)
    max_ttl_seconds: int = Field(gt=0)
    null_value_enabled: bool
    null_value_ttl_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_clients(self) -> "CacheSettings":
        """客户端名称唯一，默认客户端必须已声明；启用缓存时至少要有一个客户端。"""
        names = [client.name for client in self.clients]
        if len(names) != len(set(names)):
            raise ValueError("Redis 客户端名称不能重复")
        if self.enabled and not names:
            raise ValueError("启用缓存必须至少声明一个 Redis 客户端")
        if self.enabled and self.default_client not in names:
            raise ValueError(f"默认 Redis 客户端未声明: {self.default_client}")
        if self.username is not None and self.password is None:
            raise ValueError("Redis 用户名必须与密码同时配置")
        if self.null_value_enabled and self.null_value_ttl_seconds > self.max_ttl_seconds:
            raise ValueError("空值缓存 TTL 不能超过 max_ttl_seconds")
        return self
