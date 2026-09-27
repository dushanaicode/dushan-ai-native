from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.common.exception import ServiceException
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.public import (
    AuthErrorCodes,
    AuthException,
)
from framework.starter_web.public import (
    RequestContext,
)
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.framework.social.model.social_auth_config import SocialAuthConfig
from module_system.service.social.social_client_service_impl import SocialClientServiceImpl
from module_system.spi.social.social_client_provider_adapter import SocialClientProviderAdapter

VALID_CONFIG = {
    "redirect_uri": "https://app.example/callback",
    "scopes": ["snsapi_base"],
    "pkce": False,
    "options": {},
    "credentials": {},
}


async def test_disabled_auth_hides_login_providers_without_querying_clients():
    service = SocialClientServiceImpl()
    service.auth = SimpleNamespace(settings=SimpleNamespace(enabled=False))
    service.social_client_mapper = SimpleNamespace(select_list_by_status=AsyncMock())
    assert await service.get_login_providers() == []
    service.social_client_mapper.select_list_by_status.assert_not_awaited()


def test_social_types_cover_every_builtin_auth_source_and_callback_contract():
    registry = AuthProviderRegistry()
    service = SocialClientServiceImpl()
    service.auth = SimpleNamespace(
        registry=registry, callback_parameter=lambda source: registry.get(source).callback_code
    )
    choices = service.get_provider_types()
    assert {item.source for item in choices} == {item.source for item in registry.capabilities()}
    assert len(choices) == len({item.type for item in choices}) == 36
    assert {item.source for item in choices if item.mode == "native"} == {
        "WECHAT_MINI_PROGRAM",
        "QQ_MINI_PROGRAM",
    }
    callbacks = {item.source: item.code_parameter for item in choices}
    assert callbacks["DINGTALK_V2"] == "authCode"
    assert callbacks["ALIPAY"] == "auth_code"
    assert callbacks["WECHAT_ENTERPRISE"] == "code"


def test_empty_auth_config_is_a_valid_shape():
    config = SocialAuthConfig.model_validate({})
    assert config.redirect_uri is None and config.scopes == ()
    assert config.pkce is False and config.options == {} and config.credentials == {}


@pytest.mark.parametrize(
    "value",
    [
        {"redirectUri": "https://app.example/callback"},
        {"scopes": "snsapi_base"},
        {"credentials": {"alipay_public_key": 1}},
    ],
)
def test_stored_auth_config_errors_stay_inside_auth_contract(value):
    with pytest.raises(AuthException) as failure:
        SocialClientProviderAdapter._auth_config(value)
    assert failure.value.error_code == AuthErrorCodes.CONFIG
    assert failure.value.outcome == "not_sent"


def test_stored_auth_config_accepts_declared_fields():
    config = SocialClientProviderAdapter._auth_config(VALID_CONFIG)
    assert config.redirect_uri == "https://app.example/callback" and config.scopes == (
        "snsapi_base",
    )


@pytest.mark.parametrize(
    "value",
    [
        {"redirectUri": "https://app.example/callback"},
        {"scopes": "snsapi_base"},
        {"credentials": {"alipay_public_key": 1}},
    ],
)
def test_saving_invalid_auth_config_reports_fields_without_values(value):
    with pytest.raises(ServiceException) as failure:
        SocialClientServiceImpl._validate_auth_config(value)
    assert failure.value.error_code == ErrorCodeConstants.SOCIAL_CLIENT_AUTH_CONFIG_INVALID
    assert "https://app.example/callback" not in failure.value.msg
    assert "alipay_public_key" not in failure.value.msg or "credentials" in failure.value.msg


def test_saving_declared_auth_config_passes():
    SocialClientServiceImpl._validate_auth_config(VALID_CONFIG)


@pytest.mark.parametrize("value", [{}, {"credentials": {}}, VALID_CONFIG])
def test_channels_without_vendor_credentials_can_be_saved(value):
    """多数渠道不需要额外凭据；空 credentials 在创建和更新两条路径都必须放行。"""
    SocialClientServiceImpl._validate_auth_config(value)


def test_blank_vendor_credential_reports_business_error():
    with pytest.raises(ServiceException) as failure:
        SocialClientServiceImpl._validate_auth_config(
            {**VALID_CONFIG, "credentials": {"alipay_secret": "  "}}
        )
    assert failure.value.error_code == ErrorCodeConstants.SOCIAL_CLIENT_AUTH_CONFIG_INVALID
    assert "alipay_secret" in failure.value.msg


async def test_auth_user_sends_the_channel_callback_parameter(monkeypatch):
    captured = {}

    class FakeAuthService:
        @staticmethod
        def callback_parameter(source):
            return "auth_code" if source == "ALIPAY" else "code"

        @staticmethod
        async def complete(application_id, source, parameters, *, binding):
            captured.update(
                application_id=application_id,
                source=source,
                parameters=list(parameters),
                binding=binding,
            )
            return "auth-result"

    monkeypatch.setattr(
        RequestContext,
        "current",
        staticmethod(
            lambda: SimpleNamespace(
                connection=SimpleNamespace(cookies={"system_social_binding": "b" * 48})
            )
        ),
    )
    service = SocialClientServiceImpl()
    service.auth = FakeAuthService()
    service.settings = SimpleNamespace(application_id="dushan")
    service.tenant_context = SimpleNamespace(get_required_tenant_id=lambda: "1")
    service.cache_handler = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(hit=True, value="1")), delete=AsyncMock()
    )
    result = await service.get_auth_user(SocialTypeEnum.ALIPAY.code, 2, "vendor-code", "state")
    assert result == "auth-result"
    service.cache_handler.delete.assert_awaited_once()
    assert captured["parameters"] == [("auth_code", "vendor-code"), ("state", "state")]
    assert captured["application_id"] == "dushan-admin" and captured["source"] == "ALIPAY"
