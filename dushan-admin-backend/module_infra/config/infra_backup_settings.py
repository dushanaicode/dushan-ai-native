from pydantic import Field

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


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
