from pydantic import BaseModel, ConfigDict, Field, JsonValue


class CaptchaChallenge(BaseModel):
    """公开挑战只含呈现信息；答案不进入此对象。"""

    model_config = ConfigDict(frozen=True)
    token: str = Field(repr=False)
    provider: str
    purpose: str
    expires_in: int
    data: dict[str, JsonValue] = Field(repr=False)
