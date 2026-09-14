from pydantic import BaseModel, ConfigDict, Field, model_validator


class LockRule(BaseModel):
    """不可重入、无续租；协作式取消不能中止阻塞线程或外部已提交的操作。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lease_ms: int = Field(strict=True, ge=1, le=86_400_000)
    wait_ms: int = Field(strict=True, ge=0, le=60_000)
    execution_timeout_ms: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def validate_deadline(self) -> "LockRule":
        if self.execution_timeout_ms >= self.lease_ms:
            raise ValueError("execution_timeout_ms 必须严格小于 lease_ms")
        return self
