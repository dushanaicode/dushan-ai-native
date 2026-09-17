from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer


class CaptchaCheckReqVO(BaseRequestVO):
    challenge_id: str
    purpose: str
    answer: CaptchaAnswer
