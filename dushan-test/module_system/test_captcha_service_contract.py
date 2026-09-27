import pytest

from framework.starter_captcha.definitions.constants.captcha_error_codes import (
    CaptchaErrorCodes as Codes,
)
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from module_system.service.captcha.captcha_service_impl import CaptchaServiceImpl

TOKEN = "v" * 43


class _Settings:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled


class _Delegate:
    def __init__(self, error: CaptchaException | None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def consume(self, verification: str, purpose: str) -> None:
        self.calls.append((verification, purpose))
        if self.error is not None:
            raise self.error


class _ReqVO:
    verification = TOKEN


def build(enabled: bool, error: CaptchaException | None = None) -> CaptchaServiceImpl:
    """Inject 字段允许手工赋值用于独立测试，这里不进入容器。"""
    service = CaptchaServiceImpl()
    service.settings = _Settings(enabled)
    service.delegate = _Delegate(error)
    return service


async def test_disabled_captcha_passes_without_consuming():
    service = build(enabled=False)
    assert await service.verification(_ReqVO()) is True
    assert service.delegate.calls == []


async def test_consumed_credential_reports_success_once():
    service = build(enabled=True)
    assert await service.verification(_ReqVO()) is True
    assert service.delegate.calls == [(TOKEN, "login")]


@pytest.mark.parametrize("purpose", ["login", "register"])
async def test_business_rejection_returns_false_instead_of_always_true(purpose):
    """凭证无效必须能让调用方写登录日志并给出自己的业务错误码，不能被报成通过。"""
    service = build(enabled=True, error=CaptchaException(Codes.INVALID_VERIFICATION))
    assert await service.verification(_ReqVO(), purpose=purpose) is False
    assert service.delegate.calls == [(TOKEN, purpose)]


@pytest.mark.parametrize("code", [Codes.CACHE_UNAVAILABLE, Codes.CORRUPT, Codes.UNAVAILABLE])
async def test_system_failures_are_not_downgraded_to_wrong_captcha(code):
    service = build(enabled=True, error=CaptchaException(code))
    with pytest.raises(CaptchaException) as error:
        await service.verification(_ReqVO())
    assert error.value.error_code == code and error.value.is_system_error is True
