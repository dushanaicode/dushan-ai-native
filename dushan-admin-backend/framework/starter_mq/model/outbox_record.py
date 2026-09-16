from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from framework.starter_mq.enums.outbox_state import OutboxState
from framework.starter_mq.model.prepared_message import PreparedMessage


class OutboxRecord(BaseModel):
    """公共持久化契约；正式表和业务数据使用同一个受管事务。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1, max_length=128)
    message: PreparedMessage
    state: OutboxState
    attempts: int = Field(strict=True, ge=0)
    created_at: AwareDatetime
    ready_at: AwareDatetime
    claim_token: str | None
    claim_expires_at: AwareDatetime | None
    finished_at: AwareDatetime | None
    error_type: str | None
