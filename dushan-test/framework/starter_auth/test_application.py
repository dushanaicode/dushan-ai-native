import json
import os

import httpx
import pytest

from fixtures.public_web_app import create_public_app
from framework.starter_auth.core.auth_service import AuthService
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.starter.auth_starter import AuthStarter
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_di.decorators.di_dependency import DiDependency

from .support import BINDING, CHANNEL_RESPONSES, SECRET, RecordingTransport, client_config


def application_values(*, auth_enabled=True, cache_enabled=True):
    target = json.loads(os.environ.get("DUSHAN_AUTH_TEST_REDIS", "null"))
    if target is None and cache_enabled:
        pytest.skip("需要本轮私有 Redis")
    config = client_config().model_dump()
    config.update(client_secret=SECRET, credentials={})
    cache = {"enabled": cache_enabled}
    if target is not None:
        cache.update(
            host=target["host"],
            port=target["port"],
            default_client="auth_store",
            clients=[{"name": "auth_store", "db": 1}],
        )
    return {
        "banner": {"enabled": False},
        "config": {
            "models": {
                "auth": {"enabled": auth_enabled, "client_name": "auth_store", "clients": [config]},
                "cache": cache,
            }
        },
    }


async def test_application_di_named_cache_and_callback(config_dir):
    from fastapi import Depends, Request

    app = create_public_app(base_dir=config_dir(application_values()), environ={})

    @app.get("/auth-test/start")
    async def begin(service=Depends(DiDependency(AuthService))):
        return await service.begin("app-a", "GITHUB", binding=BINDING)

    @app.get("/auth-test/callback")
    async def callback(request: Request, service=Depends(DiDependency(AuthService))):
        return await service.complete(
            "app-a", "GITHUB", request.query_params.multi_items(), binding=BINDING
        )

    async with app.router.lifespan_context(app):
        service = app.state.auth
        assert service.is_ready
        transport = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
        service._transport = transport
        with app.state.application_context.execution():
            assert app.state.application_context.get_bean(AuthService) is service
            assert app.state.application_context.get_bean(AuthStarter).service is service
            registry = app.state.application_context.get_bean(CacheKeyRegistry)
            assert registry.is_registered
            assert service.store.key.client_name == "auth_store"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://app.test"
        ) as browser:
            request = await browser.get("/auth-test/start")
            assert request.status_code == 200
            content = request.json()
            state = content["state"]
            response = await browser.get(
                "/auth-test/callback", params={"state": state, "code": "one-time-code"}
            )
            result = response.json()
            assert result["identity"]["subject"] == "123"
            assert "tokens" not in result
            assert SECRET not in response.text
    assert app.state.auth is None and service._http.client.is_closed
    assert app.state.application_context is None


async def test_disabled_auth_has_no_network_resources(config_dir):
    app = create_public_app(
        base_dir=config_dir(application_values(auth_enabled=False, cache_enabled=False)), environ={}
    )
    async with app.router.lifespan_context(app):
        assert app.state.auth is None
        with app.state.application_context.execution():
            service = app.state.application_context.get_bean(AuthService)
            assert service._http is None
            with pytest.raises(AuthException) as error:
                await service.begin("app-a", "GITHUB", binding=BINDING)
            assert error.value.error_code == Codes.DISABLED


async def test_enabled_auth_requires_actual_cache(config_dir):
    app = create_public_app(
        base_dir=config_dir(application_values(cache_enabled=False)), environ={}
    )
    with pytest.raises(Exception):
        async with app.router.lifespan_context(app):
            pytest.fail("缺少 Cache 不能进入就绪")
    assert app.state.auth is None and app.state.application_context is None


async def test_scanned_provider_extension(config_dir, module_package):
    module_package(
        "auth_extension",
        files={
            "provider.py": """
from framework.starter_scanner.annotation.scanner_decorator import scanner
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.model.provider_capability import ProviderCapability

@scanner
class ExtensionProvider(OAuthProvider):
    capabilities = (ProviderCapability("EXTENSION"),)
    authorization_endpoint = "https://issuer.example/authorize"
    token_endpoint = "https://issuer.example/token"
    userinfo_endpoint = "https://issuer.example/user"
"""
        },
        scan_roots=(".",),
    )
    values = application_values()
    values["config"]["models"]["auth"]["clients"][0].update(source="EXTENSION", pkce=False)
    values["modules"] = {
        "packages": ["framework", "auth_extension"],
        "enabled": ["framework", "auth_extension"],
    }
    app = create_public_app(base_dir=config_dir(values), environ={})
    async with app.router.lifespan_context(app):
        assert app.state.auth.registry.capability("EXTENSION").source == "EXTENSION"
        service = app.state.auth
        service._transport = RecordingTransport(
            [
                {"access_token": "extension-access", "expires_in": 600},
                {"id": "extension-user"},
            ]
        )
        with app.state.application_context.execution():
            request = await service.begin("app-a", "EXTENSION", binding=BINDING)
            result = await service.complete(
                "app-a", "EXTENSION", [("state", request.state), ("code", "code")], binding=BINDING
            )
            assert (
                result.identity.subject == "extension-user" and result.identity.subject_type == "id"
            )


async def test_di_decorator_is_not_a_provider_registration(config_dir, module_package):
    from server.bootstrap.bootstrapper import BootstrapError

    module_package(
        "auth_wrong_decoration",
        files={
            "provider.py": """
from framework.starter_di.decorators.components import framework
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.model.provider_capability import ProviderCapability

@framework
class WrongProvider(OAuthProvider):
    capabilities = (ProviderCapability("WRONG_DECORATION"),)
    authorization_endpoint = "https://issuer.example/authorize"
"""
        },
        scan_roots=(".",),
    )
    values = application_values()
    values["modules"] = {
        "packages": ["framework", "auth_wrong_decoration"],
        "enabled": ["framework", "auth_wrong_decoration"],
    }
    app = create_public_app(base_dir=config_dir(values), environ={})
    with pytest.raises(BootstrapError):
        async with app.router.lifespan_context(app):
            pytest.fail("@framework 不能替代非 DI 管理的 Provider 扫描声明")
    assert app.state.application_context is None and app.state.auth is None
