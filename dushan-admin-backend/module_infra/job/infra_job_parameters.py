from pydantic import Field

from framework.common.schemas import BaseBO


class InfraJobParameters(BaseBO):
    retain_days: int = Field(default=14, ge=1)
    batch_size: int = Field(default=100, ge=1, le=1000)
