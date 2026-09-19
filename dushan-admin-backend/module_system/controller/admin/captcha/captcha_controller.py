from fastapi import APIRouter, Depends

from framework.starter_captcha.public import (
    CaptchaChallenge,
    CaptchaVerification,
)
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_web.public import (
    AccessLogPolicy,
    Result,
    RoutePolicy,
)
from module_system.controller.admin.captcha.vo.captcha_check_req_vo import CaptchaCheckReqVO
from module_system.controller.admin.captcha.vo.captcha_get_req_vo import CaptchaGetReqVO
from module_system.service.captcha.captcha_service import CaptchaService

captcha_controller = APIRouter(prefix="/captcha", tags=["System - 验证码"])


class CaptchaController:
    @staticmethod
    @captcha_controller.get("/config")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def captcha_config(
        service: CaptchaService = Depends(DiDependency(CaptchaService)),
    ):
        return Result.success(service.configuration())

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
