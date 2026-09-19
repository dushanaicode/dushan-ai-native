from pydantic import Field

from framework.starter_config.public import (
    ConfigModel,
    ConfigSourceEnum,
    config_model,
)


@config_model(
    "infra_backup",
    env_prefix="INFRA_BACKUP_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class InfraBackupSettings(ConfigModel):
    enabled: bool
    executable: str = Field(min_length=1)
    output_directory: str = Field(min_length=1)
    data_source: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0, le=86400)
