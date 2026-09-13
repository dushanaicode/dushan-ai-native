from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from framework.starter_captcha.model.captcha_point import CaptchaPoint


class CaptchaRecord(BaseModel):
    """仅在服务端缓存中流转的答案记录，与公开响应分别建模。"""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    provider: Literal["block_puzzle", "click_word", "aliyun", "tencent"]
    purpose: str
    points: list[CaptchaPoint] = Field(max_length=3, repr=False)
