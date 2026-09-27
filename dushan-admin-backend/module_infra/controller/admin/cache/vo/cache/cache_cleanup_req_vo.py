from typing import Literal

from pydantic import Field, model_validator

from framework.common.schemas import BaseRequestVO


class CacheCleanupReqVO(BaseRequestVO):
    preset: Literal["business", "authentication", "mq", "jobs"]
    db_name: str = Field(min_length=1, max_length=63)
    confirmation: Literal["CLEAR"] | None = None

    @model_validator(mode="after")
    def require_confirmation(self):
        if self.preset != "business" and self.confirmation != "CLEAR":
            raise ValueError("高风险清理必须明确输入 CLEAR 确认")
        return self
