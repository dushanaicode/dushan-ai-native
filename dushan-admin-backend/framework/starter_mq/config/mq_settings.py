from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator

from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
from framework.starter_mq.definitions.enums.mq_backend import MQBackend
from framework.starter_mq.model.consumer_override import ConsumerOverride


@config_model("mq", env_prefix="MQ_", sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML))
class MQSettings(ConfigModel):
    enabled: bool
    backend: MQBackend
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    cache_client: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    signing_secret: SecretStr | None
    max_age_seconds: int = Field(strict=True, ge=1)
    clock_skew_seconds: float = Field(ge=0, allow_inf_nan=False)
    replay_retention_seconds: int = Field(strict=True, ge=1)
    lease_seconds: float = Field(gt=0, allow_inf_nan=False)
    renew_seconds: float = Field(gt=0, allow_inf_nan=False)
    command_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    handler_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    shutdown_seconds: float = Field(gt=0, allow_inf_nan=False)
    poll_seconds: float = Field(gt=0, allow_inf_nan=False)
    concurrency: int = Field(strict=True, ge=1)
    prefetch: int = Field(strict=True, ge=1)
    max_consumers: int = Field(strict=True, ge=1)
    max_concurrency: int = Field(strict=True, ge=1)
    max_prefetch: int = Field(strict=True, ge=1)
    max_message_bytes: int = Field(strict=True, ge=1)
    max_proof_bytes: int = Field(strict=True, ge=1, le=65536)
    stream_max_length: int = Field(strict=True, ge=1)
    retry_max_length: int = Field(strict=True, ge=1)
    dead_letter_max_length: int = Field(strict=True, ge=1)
    dead_letter_retention_seconds: int = Field(strict=True, ge=1)
    max_retry_delay_seconds: float = Field(gt=0, allow_inf_nan=False)
    overrides: dict[str, ConsumerOverride]
    unknown_override: Literal["fail", "ignore"]
    rabbit_url: SecretStr | None
    rabbit_ca_file: Path | None
    kafka_bootstrap_servers: tuple[str, ...]
    kafka_security_protocol: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
    kafka_sasl_mechanism: Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"] | None
    kafka_sasl_username: str | None
    kafka_sasl_password: SecretStr | None
    kafka_ca_file: Path | None
    kafka_cert_file: Path | None
    kafka_key_file: Path | None
    kafka_partitions: int = Field(strict=True, ge=1)
    kafka_replication_factor: int = Field(strict=True, ge=1)
    kafka_retention_bytes: int = Field(strict=True, ge=1)
    outbox_enabled: bool
    outbox_batch_size: int = Field(strict=True, ge=1)
    outbox_max_attempts: int = Field(strict=True, ge=1)
    outbox_lease_seconds: float = Field(gt=0, allow_inf_nan=False)
    outbox_retry_seconds: float = Field(gt=0, allow_inf_nan=False)
    outbox_retention_seconds: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.renew_seconds + self.command_timeout_seconds >= self.lease_seconds:
            raise ValueError("MQ 续租和命令上界必须小于租约")
        if self.replay_retention_seconds < self.max_age_seconds + self.clock_skew_seconds:
            raise ValueError("MQ 防重放保留期必须覆盖签名有效期")
        if (
            not self.concurrency <= self.prefetch <= self.max_prefetch
            or self.concurrency > self.max_concurrency
        ):
            raise ValueError("MQ 并发和预取超过声明上界")
        if self.outbox_lease_seconds <= self.command_timeout_seconds:
            raise ValueError("Outbox 租约必须覆盖一次发布上界")
        if self.enabled:
            if (
                self.signing_secret is None
                or len(self.signing_secret.get_secret_value().encode()) < 32
            ):
                raise ValueError("MQ 必须显式设置至少 32 字节签名密钥")
            if self.backend is MQBackend.RABBITMQ and self.rabbit_url is None:
                raise ValueError("RabbitMQ 必须显式配置连接")
            if self.backend is MQBackend.KAFKA and not self.kafka_bootstrap_servers:
                raise ValueError("Kafka 必须显式配置连接")
        sasl = self.kafka_security_protocol.startswith("SASL_")
        if sasl != all(
            v is not None
            for v in (self.kafka_sasl_mechanism, self.kafka_sasl_username, self.kafka_sasl_password)
        ):
            raise ValueError("Kafka SASL 配置不完整")
        if not sasl and any(
            v is not None
            for v in (self.kafka_sasl_mechanism, self.kafka_sasl_username, self.kafka_sasl_password)
        ):
            raise ValueError("非 SASL 协议不能配置 SASL 凭证")
        if (self.kafka_cert_file is None) != (self.kafka_key_file is None):
            raise ValueError("Kafka 客户端证书和私钥必须成对配置")
        return self

    def cache_key(self) -> CacheKey:
        return CacheKey(key="mq", remark="消息运行时原生 Redis 数据", client_name=self.cache_client)
