from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator


class JobDefinition(BaseModel):
    """业务 SPI 的唯一计划快照；只保存稳定 key 和 JSON 参数，不保存可执行引用。"""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)
    id: str = Field(min_length=1, max_length=128)
    handler_key: str = Field(pattern=r"^[a-z][a-z0-9_.:-]{0,127}$")
    parameters: dict[str, JsonValue]
    cron: str
    enabled: bool
    revision: str = Field(min_length=1, max_length=128)
    effective_at: AwareDatetime = Field(description="当前版本生效时间，与 revision 一起更新")
    max_instances: int = Field(strict=True, ge=1)
    timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    max_retries: int = Field(strict=True, ge=0, le=100)
    retry_seconds: float = Field(ge=0, le=86400, allow_inf_nan=False)
    retry_backoff: float = Field(ge=1, le=10, allow_inf_nan=False)
    stop_after_failure: bool
    tenant_id: str | None
    fan_out: bool

    @model_validator(mode="after")
    def validate_target(self):
        if self.fan_out and self.tenant_id is not None:
            raise ValueError("扇出计划不同时固定单个租户")
        return self
