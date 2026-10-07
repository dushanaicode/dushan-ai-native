from pydantic import Field

from framework.common.schemas import BaseBO


class EmailResetStateBO(BaseBO):
    code_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    user_id: int | None
    credential_revision: int | None
    issued_at: float = Field(gt=0, allow_inf_nan=False)
    expires_at: float = Field(gt=0, allow_inf_nan=False)
    attempts: int = Field(ge=0)
    daily_count: int = Field(ge=1)
