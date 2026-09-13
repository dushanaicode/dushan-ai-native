from abc import ABC, abstractmethod

from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.model.captcha_record import CaptchaRecord


class CaptchaProvider(ABC):
    """本地和云 Provider 共用的实际边界；实例由本应用持有。"""

    @abstractmethod
    def create(self, purpose: str) -> tuple[dict, CaptchaRecord]:
        """返回公开呈现信息及独立的服务端答案。"""

    @abstractmethod
    async def verify(
        self, record: CaptchaRecord, answer: CaptchaAnswer, client_ip: str | None
    ) -> bool:
        """判断本次回答；依赖失败抛异常，绝不转成通过。"""
