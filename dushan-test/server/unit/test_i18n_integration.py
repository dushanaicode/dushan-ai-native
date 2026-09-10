import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.registry.error_code_registry import ErrorCodeRegistry
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigError
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app

pytestmark = pytest.mark.unit


def add_error_routes(app):
    """以真实 HTTP 错误覆盖应用装配及错误响应翻译链路。"""

    @app.get("/gateway-failure")
    async def gateway_failure():
        raise HTTPException(status_code=502, detail="上游暂不可用")

    @app.get("/bad-request")
    async def bad_request():
        raise HTTPException(status_code=400, detail="请求不正确")

    @app.get("/forbidden")
    async def forbidden():
        raise HTTPException(status_code=403, detail="拒绝访问")


def test_application_lifespan_injects_translator_and_translates_http_errors(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    add_error_routes(app)
    handler = app.state.bootstrap.exception_handler
    assert handler.translator is None
    with TestClient(app, raise_server_exceptions=False) as client:
        assert handler.translator is not None
        gateway = client.get("/gateway-failure", headers={"Accept-Language": "en-US"})
        assert gateway.status_code == 502
        assert gateway.json()["code"] == GlobalErrorCodeConstants.BAD_GATEWAY.code
        assert gateway.json()["msg"] == "Bad gateway"
        request = client.get("/bad-request", headers={"Accept-Language": "en-US"})
        assert request.status_code == 400
        assert request.json()["msg"] == "Invalid request parameters"
        forbidden = client.get("/forbidden", headers={"Accept-Language": "en-US"})
        assert forbidden.status_code == 403
        assert forbidden.json()["msg"] == "No permission for this operation"
        missing = client.get("/no-such-route", headers={"Accept-Language": "en-US"})
        assert missing.status_code == 404
        assert missing.json()["msg"] == "Request not found"
        assert client.get("/health").status_code == 200
    assert handler.translator is None


def test_disabled_i18n_preserves_final_http_detail_without_loading_resources(config_dir):
    root = config_dir(
        {
            "i18n": {
                "enabled": False,
                "include_builtin": False,
                "resource_roots": [{"path": "absent", "scope": "custom", "required": True}],
            }
        }
    )
    app = create_app(base_dir=root, environ={})
    add_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/bad-request", headers={"Accept-Language": "en-US"})
        assert response.status_code == 400
        assert response.json()["msg"] == "请求不正确"


@pytest.mark.parametrize("vary", [None, "Accept-Encoding", "accept-language", "*"])
def test_localized_errors_preserve_headers_and_declare_language_variation(config_dir, vary):
    """共享缓存按语言区分异常响应，原认证与重试响应头保持有效。"""
    app = create_app(base_dir=config_dir(), environ={})
    headers = {"WWW-Authenticate": "Bearer", "Retry-After": "3"}
    if vary is not None:
        headers["vary"] = vary

    @app.get("/challenge")
    async def challenge():
        raise HTTPException(status_code=401, headers=headers)

    with TestClient(app) as client:
        response = client.get("/challenge", headers={"Accept-Language": "en-US"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.headers["retry-after"] == "3"
        tokens = [value.strip().lower() for value in response.headers["vary"].split(",")]
        if vary == "*":
            assert tokens == ["*"]
        else:
            assert tokens.count("accept-language") == 1
            if vary == "Accept-Encoding":
                assert "accept-encoding" in tokens
    assert headers.get("vary") == vary


def test_configuration_alone_adds_french_with_relative_resource_root(config_dir):
    root = config_dir(
        {
            "i18n": {
                "default_locale": "fr-FR",
                "supported_locales": ["fr-FR"],
                "include_builtin": False,
                "validate_translations": False,
                "resource_roots": [{"path": "custom", "scope": "framework"}],
            }
        }
    )
    resources = root / "custom"
    resources.mkdir()
    (resources / "fr-FR.json").write_text(
        json.dumps({"exception.bad_gateway": "Passerelle indisponible"}), encoding="utf-8"
    )
    app = create_app(base_dir=root, environ={})
    add_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/gateway-failure", headers={"Accept-Language": "fr"})
        assert response.status_code == 502
        assert response.json()["msg"] == "Passerelle indisponible"
        catalog = app.state.bootstrap.exception_handler.translator.catalog
        assert set(catalog.bundles) == {"fr-FR"}


def test_configuration_can_require_business_translations(config_dir):
    """业务模块通过配置声明必需键，缺语言阻止启动，补资源后无需改框架。"""
    root = config_dir({"i18n": {"resource_roots": [{"path": "account", "scope": "account"}]}})
    resources = root / "account"
    resources.mkdir()
    (resources / "en-US.json").write_text('{"account.greeting":"Welcome"}', encoding="utf-8")
    environ = {"I18N_REQUIRED_MESSAGE_KEYS": '["account.greeting"]'}
    with (
        pytest.raises(BootstrapError) as error,
        TestClient(create_app(base_dir=root, environ=environ)),
    ):
        pass
    assert "account.greeting" in str(error.value.__cause__)
    (resources / "zh-CN.json").write_text('{"account.greeting":"欢迎"}', encoding="utf-8")
    app = create_app(base_dir=root, environ=environ)
    with TestClient(app):
        translator = app.state.bootstrap.exception_handler.translator
        assert translator.translate_any_scope("account.greeting", "en-US") == "Welcome"
        assert translator.translate_any_scope("account.greeting", "zh-CN") == "欢迎"


def test_i18n_environment_configuration_overrides_yaml(config_dir):
    app = create_app(
        base_dir=config_dir(),
        environ={
            "I18N_DEFAULT_LOCALE": "en-US",
            "I18N_SUPPORTED_LOCALES": '["en-US", "zh-CN"]',
            "I18N_MATCH_MODE": "exact",
            "I18N_CACHE_SIZE": "0",
            "I18N_LOG_MISSING": "false",
        },
    )
    add_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        options = app.state.bootstrap.exception_handler.translator.catalog.options
        assert options.default_locale == "en-US"
        assert options.supported_locales == ("en-US", "zh-CN")
        assert options.match_mode == "exact"
        assert options.cache_size == 0
        assert options.log_missing is False
        response = client.get("/gateway-failure")
        assert response.json()["msg"] == "Bad gateway"


@pytest.mark.parametrize(
    "i18n",
    [
        {"supported_locales": ["zh-CN", "en-US", "fr-FR"]},
        {"include_builtin": False},
        {"resource_roots": [{"path": "absent", "scope": "custom"}]},
    ],
)
def test_strict_i18n_failure_prevents_startup_and_releases_previous_resources(config_dir, i18n):
    app = create_app(base_dir=config_dir({"i18n": i18n}), environ={})
    with pytest.raises(BootstrapError) as error, TestClient(app):
        pass
    assert isinstance(error.value.__cause__, ConfigurationException)
    context = app.state.bootstrap
    assert context.ready is False
    assert context.exception_handler.translator is None
    assert context.logging_starter.initialized is False


def test_validation_warning_allows_incomplete_additional_language(config_dir):
    app = create_app(
        base_dir=config_dir(
            {
                "i18n": {
                    "supported_locales": ["zh-CN", "en-US", "fr-FR"],
                    "validation_policy": "warning",
                }
            }
        ),
        environ={},
    )
    add_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/bad-request", headers={"Accept-Language": "fr-FR"})
        assert response.json()["msg"] == "请求参数不正确"


@pytest.mark.parametrize("i18n", [{"unknown_option": True}, {"reload_interval": 0}])
def test_invalid_i18n_configuration_fails_during_application_creation(config_dir, i18n):
    with pytest.raises(BootstrapConfigError):
        create_app(base_dir=config_dir({"i18n": i18n}), environ={})


def test_multiple_applications_keep_translations_isolated_and_registry_unchanged(config_dir):
    root = config_dir()
    initial_registry = ErrorCodeRegistry.get_all_detail()
    initial_initialized = ErrorCodeRegistry.is_initialized()
    for name in ("first", "second"):
        resources = root / name
        resources.mkdir()
        (resources / "en-US.json").write_text(
            json.dumps({"exception.bad_gateway": f"Gateway for {name}"}), encoding="utf-8"
        )

    def create(name):
        return create_app(
            base_dir=root,
            environ={"I18N_RESOURCE_ROOTS": json.dumps([{"path": name, "scope": "framework"}])},
        )

    first, second = create("first"), create("second")
    add_error_routes(first)
    add_error_routes(second)
    with TestClient(first, raise_server_exceptions=False) as a:
        first_translator = first.state.bootstrap.exception_handler.translator
        with TestClient(second, raise_server_exceptions=False) as b:
            assert first_translator is not second.state.bootstrap.exception_handler.translator
            assert (
                a.get("/gateway-failure", headers={"Accept-Language": "en-US"}).json()["msg"]
                == "Gateway for first"
            )
            assert (
                b.get("/gateway-failure", headers={"Accept-Language": "en-US"}).json()["msg"]
                == "Gateway for second"
            )
        assert second.state.bootstrap.exception_handler.translator is None
        assert (
            a.get("/gateway-failure", headers={"Accept-Language": "en-US"}).json()["msg"]
            == "Gateway for first"
        )
    assert first.state.bootstrap.exception_handler.translator is None
    assert ErrorCodeRegistry.get_all_detail() == initial_registry
    assert ErrorCodeRegistry.is_initialized() is initial_initialized


@pytest.mark.parametrize("hot_reload", [False, True])
def test_configured_http_hot_reload_retains_last_valid_translation(
    config_dir, monkeypatch, hot_reload
):
    clock = [100.0]
    monkeypatch.setattr("framework.common.i18n.core.reloader.monotonic", lambda: clock[0])
    root = config_dir(
        {
            "i18n": {
                "hot_reload": hot_reload,
                "reload_interval": 1,
                "resource_roots": [{"path": "custom", "scope": "framework"}],
            }
        }
    )
    resources = root / "custom"
    resources.mkdir()
    resource = resources / "en-US.json"
    resource.write_text('{"exception.bad_gateway":"Before"}', encoding="utf-8")
    app = create_app(base_dir=root, environ={})
    add_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = {"Accept-Language": "en-US"}
        assert client.get("/gateway-failure", headers=headers).json()["msg"] == "Before"
        resource.write_text('{"exception.bad_gateway":"After"}', encoding="utf-8")
        clock[0] += 2
        expected = "After" if hot_reload else "Before"
        assert client.get("/gateway-failure", headers=headers).json()["msg"] == expected
        resource.write_text("{", encoding="utf-8")
        clock[0] += 2
        assert client.get("/gateway-failure", headers=headers).json()["msg"] == expected
        resource.unlink()
        clock[0] += 2
        assert client.get("/gateway-failure", headers=headers).json()["msg"] == (
            "Bad gateway" if hot_reload else "Before"
        )
