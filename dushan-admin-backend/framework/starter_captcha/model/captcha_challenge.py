from pydantic import BaseModel, ConfigDict, Field, JsonValue


class CaptchaChallenge(BaseModel):
    """公开挑战只含呈现信息；答案不进入此对象。

    这是前端直接消费的线上契约：字段保持 snake_case，不套用 BaseVO 的 camelCase 别名，
    data 内各 Provider 子协议的键同样保持 snake_case。
    token 即回传 /captcha/check 时的 challengeId，同一值在两端各用一个名字。
    """

    model_config = ConfigDict(frozen=True)
    token: str = Field(repr=False)
    provider: str
    purpose: str
    expires_in: int
    data: dict[str, JsonValue] = Field(repr=False)
