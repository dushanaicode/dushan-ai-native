from __future__ import annotations

from framework.starter_captcha.public import (
    CaptchaService as FrameworkCaptchaService,
)
from framework.starter_captcha.public import (
    CaptchaSettings,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_web.public import (
    RequestContext,
)
from module_system.service.captcha.captcha_service import CaptchaService


@service(interface=CaptchaService)
class CaptchaServiceImpl(CaptchaService):
    delegate: FrameworkCaptchaService = Inject()
    settings: CaptchaSettings = Inject()

    def configuration(self):
        return self.delegate.configuration()

    async def create_captcha(self, purpose: str):
        return await self.delegate.create(purpose)

    async def check_captcha(self, request):
        return await self.delegate.check(
            request.challenge_id,
            request.purpose,
            request.answer,
            client_ip=RequestContext.current().client_ip,
        )

    async def verification(self, req_vo, purpose="login") -> bool:
        if self.settings.enabled:
            await self.delegate.consume(req_vo.verification, purpose)
        return True
