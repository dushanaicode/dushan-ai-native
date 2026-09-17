from pydantic import Field

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "notification_delivery",
    env_prefix="NOTIFICATION_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
)
class NotificationDeliverySettings(ConfigModel):
    delivery_claim_lease_seconds: int = Field(ge=1)
    outbox_processing_lease_seconds: int = Field(ge=1)
    outbox_terminal_retention_days: int = Field(ge=1)
    outbox_batch_size: int = Field(ge=1, le=1000)
