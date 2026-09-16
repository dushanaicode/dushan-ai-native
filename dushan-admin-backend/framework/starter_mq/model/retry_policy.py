from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetryPolicy(BaseModel):
    """消费者代码声明的重试边界；一次投递只执行一次业务。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    count: int = Field(strict=True, ge=0, le=32)
    delay_seconds: float = Field(gt=0, allow_inf_nan=False)
    backoff: float = Field(ge=1, le=10, allow_inf_nan=False)
    max_delay_seconds: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_delay(self):
        if self.delay_seconds > self.max_delay_seconds:
            raise ValueError("重试基础间隔不能大于上界")
        return self

    def delay(self, attempt: int) -> float:
        return min(self.max_delay_seconds, self.delay_seconds * self.backoff ** (attempt - 1))
