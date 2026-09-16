import re
from math import ceil
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator

from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum
from framework.starter_websocket.enums.socket_transport import SocketTransport


@config_model(
    "websocket",
    env_prefix="WEBSOCKET_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class WebSocketSettings(ConfigModel):
    enabled: bool
    path: str = Field(pattern=r"^/api/[A-Za-z0-9][A-Za-z0-9/_-]*$")
    transport: SocketTransport
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    cache_client: str
    signing_secret: SecretStr | None
    allowed_origins: tuple[str, ...]
    subprotocols: tuple[str, ...]
    max_connections: int = Field(strict=True, ge=1)
    max_connections_per_member: int = Field(strict=True, ge=1)
    max_connections_per_tenant: int = Field(strict=True, ge=1)
    max_pending_handshakes: int = Field(strict=True, ge=1)
    handshake_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    command_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    send_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    handler_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    shutdown_seconds: float = Field(gt=0, allow_inf_nan=False)
    max_message_bytes: int = Field(strict=True, ge=128)
    inbound_queue_size: int = Field(strict=True, ge=1)
    outbound_queue_size: int = Field(strict=True, ge=1)
    handler_concurrency: int = Field(strict=True, ge=1)
    heartbeat_interval_seconds: float = Field(gt=0, allow_inf_nan=False)
    heartbeat_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    authorization_refresh_seconds: float = Field(gt=0, allow_inf_nan=False)
    authorization_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    authorization_concurrency: int = Field(strict=True, ge=1)
    instance_lease_seconds: float = Field(gt=0, allow_inf_nan=False)
    instance_renew_seconds: float = Field(gt=0, allow_inf_nan=False)
    transport_poll_seconds: float = Field(gt=0, allow_inf_nan=False)
    transport_restart_seconds: float = Field(gt=0, allow_inf_nan=False)
    envelope_max_age_seconds: float = Field(gt=0, allow_inf_nan=False)
    online_query_limit: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.enabled and (not self.allowed_origins or "*" in self.allowed_origins):
            raise ValueError("WebSocket 必须配置具体 Origin 白名单")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("WebSocket Origin 必须是无路径、无凭证的 HTTP(S) 来源")
        if len(set(self.subprotocols)) != len(self.subprotocols) or any(
            not re.fullmatch(r"[!#$%&'*+.^_`|~A-Za-z0-9-]{1,128}", protocol)
            for protocol in self.subprotocols
        ):
            raise ValueError("WebSocket 子协议必须是唯一的有效 token")
        if (
            self.enabled
            and self.transport is SocketTransport.REDIS
            and (
                self.signing_secret is None
                or len(self.signing_secret.get_secret_value().encode()) < 32
            )
        ):
            raise ValueError("Redis WebSocket 必须显式配置至少 32 字节签名密钥")
        if self.heartbeat_timeout_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("WebSocket 心跳超时必须大于心跳周期")
        maximum_round = (
            ceil(self.max_connections / self.authorization_concurrency)
            * self.authorization_timeout_seconds
        )
        if self.authorization_refresh_seconds + maximum_round >= self.heartbeat_interval_seconds:
            raise ValueError("授权刷新间隔与最坏轮次必须短于一个心跳周期")
        if (
            self.instance_renew_seconds + self.command_timeout_seconds
            >= self.instance_lease_seconds
        ):
            raise ValueError("在线实例续租和命令上界必须小于租约")
        if self.handler_concurrency > self.inbound_queue_size:
            raise ValueError("处理并发不能大于入站队列")
        return self

    def cache_key(self):
        return CacheKey(
            key="websocket", remark="WebSocket 分发与在线实例", client_name=self.cache_client
        )
