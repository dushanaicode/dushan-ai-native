from typing import Literal

from pydantic import Field, model_validator

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
from framework.starter_database.config.data_source_settings import DataSourceSettings
from framework.starter_database.config.database_pool_settings import DatabasePoolSettings


@config_model(
    "database",
    env_prefix="DATABASE_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class DatabaseSettings(ConfigModel):
    """启动期数据库契约；动态源通过显式替换入口发布，不热改连接池配置。"""

    enabled: bool
    sources: tuple[DataSourceSettings, ...]
    pool: DatabasePoolSettings
    connect_timeout_seconds: float = Field(gt=0)
    replica_strategy: Literal["round_robin", "random", "weighted", "least_connections"]
    health_check_enabled: bool
    health_check_interval_seconds: float = Field(gt=0)
    replication_check_enabled: bool
    max_replication_lag_seconds: float = Field(ge=0)
    slow_query_enabled: bool
    slow_query_threshold_ms: float = Field(ge=0)
    query_observation_enabled: bool
    query_template_enabled: bool
    query_fingerprint_enabled: bool
    query_sample_rate: float = Field(ge=0, le=1)
    query_max_statement_length: int = Field(ge=64, le=1000000)
    query_max_template_length: int = Field(ge=16, le=4096)
    dynamic_enabled: bool
    dynamic_refresh_interval_seconds: float = Field(gt=0)
    soft_delete_enabled: bool
    audit_enabled: bool
    id_strategy: Literal["database", "snowflake"]
    snowflake_machine_id: int | None = Field(ge=0, le=1023)
    after_commit_result_limit: int = Field(ge=1, le=10000)

    @model_validator(mode="after")
    def validate_sources(self) -> "DatabaseSettings":
        names = [source.name for source in self.sources]
        if len(names) != len(set(names)):
            raise ValueError("数据源名称不能重复")
        primaries = [source for source in self.sources if source.role == "primary"]
        if self.enabled and len(primaries) != 1:
            raise ValueError("启用数据库必须配置一个 primary 数据源")
        if not self.dynamic_enabled and any(source.role == "named" for source in self.sources):
            raise ValueError("具名动态源要求 dynamic_enabled=true")
        if self.enabled and self.id_strategy == "snowflake" and self.snowflake_machine_id is None:
            raise ValueError("雪花 ID 必须显式分配 snowflake_machine_id")
        return self
