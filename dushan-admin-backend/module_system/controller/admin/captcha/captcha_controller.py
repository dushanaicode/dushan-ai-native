from fastapi import APIRouter, Depends

from framework.starter_captcha.model.captcha_challenge import CaptchaChallenge
from framework.starter_captcha.model.captcha_verification import CaptchaVerification
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_web.response.result import Result
from framework.starter_web.routing.access_log_policy import AccessLogPolicy
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.captcha.vo.captcha_check_req_vo import CaptchaCheckReqVO
from module_system.controller.admin.captcha.vo.captcha_get_req_vo import CaptchaGetReqVO
from module_system.service.captcha.captcha_service import CaptchaService

captcha_controller = APIRouter(prefix="/captcha", tags=["System - 验证码"])


class CaptchaController:
    @staticmethod
    @captcha_controller.post("/get")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def get_captcha(
        req_vo: CaptchaGetReqVO, service: CaptchaService = Depends(DiDependency(CaptchaService))
    ) -> Result[CaptchaChallenge]:
        return Result.success(await service.create_captcha(req_vo.purpose))

    @staticmethod
    @captcha_controller.post("/check")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def check_captcha(
        req_vo: CaptchaCheckReqVO, service: CaptchaService = Depends(DiDependency(CaptchaService))
    ) -> Result[CaptchaVerification]:
        return Result.success(await service.check_captcha(req_vo))
