from pydantic import BaseModel, ConfigDict, Field

from framework.starter_captcha.model.captcha_point import CaptchaPoint


class CaptchaAnswer(BaseModel):
    """仅提交所选 Provider 的字段；阿里云原始参数不解析、不重新编码。"""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    points: list[CaptchaPoint] | None = Field(default=None, min_length=1, max_length=3, repr=False)
    captcha_verify_param: str | None = Field(
        default=None, min_length=1, max_length=16384, repr=False
    )
    ticket: str | None = Field(default=None, min_length=1, max_length=4096, repr=False)
    randstr: str | None = Field(default=None, min_length=1, max_length=4096, repr=False)
