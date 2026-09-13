from pydantic import BaseModel, ConfigDict, Field


class CaptchaVerification(BaseModel):
    """挑战通过后签发的短期凭证；业务执行前必须 consume，消费后不回滚。"""

    model_config = ConfigDict(frozen=True)
    verification: str = Field(repr=False)
    purpose: str
    expires_in: int
