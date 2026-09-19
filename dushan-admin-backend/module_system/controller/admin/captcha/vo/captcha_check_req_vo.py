from framework.common.schemas import BaseRequestVO
from framework.starter_captcha.public import (
    CaptchaAnswer,
)


class CaptchaCheckReqVO(BaseRequestVO):
    challenge_id: str
    purpose: str
    answer: CaptchaAnswer
