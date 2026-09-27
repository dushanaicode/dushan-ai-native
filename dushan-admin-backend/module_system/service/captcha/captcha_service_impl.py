from __future__ import annotations

from framework.starter_captcha.public import (
    CaptchaException,
    CaptchaSettings,
)
from framework.starter_captcha.public import (
    CaptchaService as FrameworkCaptchaService,
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
        """凭证消费成功返回 True；凭证无效等业务拒绝返回 False，缓存等系统故障继续上抛。

        调用方据此写登录日志并给出自己的业务错误码，因此这里不能把失败也报成通过。
        """
        if not self.settings.enabled:
            return True
        try:
            await self.delegate.consume(req_vo.verification, purpose)
        except CaptchaException as error:
            if error.is_system_error:
                raise
            return False
        return True
