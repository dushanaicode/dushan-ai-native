import json
import subprocess
from unittest.mock import Mock

import pytest

import server.launcher.server_launcher as entry
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.provider.aliyun_captcha_provider import AliyunCaptchaProvider
from framework.starter_captcha.provider.captcha_http_client import CaptchaHttpClient
from framework.starter_captcha.provider.tencent_captcha_provider import TencentCaptchaProvider
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.public import ConfigProvider
from module_system.config.system_settings import SystemSettings
from server.starter_server import StarterServer


@pytest.mark.parametrize("body", ["SERVER_PORT=65534\n", 'SERVER_PORT="unclosed\n'])
def test_application_factory_ignores_dotenv(config_dir, body):
    root = config_dir({"server": {"port": 40123}})
    (root / ".env").write_text(body, encoding="utf-8")
    application = StarterServer.create_app(base_dir=root, app_env="dev", environ={})
    assert application.state.bootstrap.settings.port == 40123


@pytest.mark.parametrize("body", ["SERVER_PORT=65534\n", 'SERVER_PORT="unclosed\n'])
def test_launcher_reads_application_files_without_dotenv(config_dir, monkeypatch, body):
    root = config_dir({"server": {"port": 40123}})
    (root / ".env").write_text(body, encoding="utf-8")
    monkeypatch.delenv("SERVER_PORT", raising=False)
    run = Mock(side_effect=lambda command, **_: subprocess.CompletedProcess(command, 0))
    monkeypatch.setattr(entry.subprocess, "run", run)
    assert entry.ServerLauncher.run(["--server", "uvicorn", "--config-dir", str(root)]) == 0
    command = run.call_args.args[0]
    assert command[command.index("--port") + 1] == "40123"
    assert "SERVER_PORT" not in run.call_args.kwargs["env"]


@pytest.mark.parametrize("value, enabled", [(None, False), (False, False), (True, True)])
def test_registration_defaults_closed_and_uses_application_yaml(config_dir, value, enabled):
    overrides = {} if value is None else {"system": {"user_register_enabled": value}}
    root = config_dir({"config": {"models": overrides}})
    bootstrap = BootstrapConfigProvider.load(root, app_env="dev", environ={})
    configuration = ConfigProvider(bootstrap, (SystemSettings,))
    try:
        assert configuration.get_config(SystemSettings).user_register_enabled is enabled
    finally:
        configuration.close()


@pytest.mark.parametrize("kind", ["tencent", "aliyun"])
def test_cloud_captcha_application_yaml_and_public_sdk_contract(config_dir, kind):
    root = config_dir(
        {
            "config": {
                "models": {
                    "captcha": {
                        "enabled": True,
                        "provider": kind,
                        "purposes": ["password_reset"],
                        "tencent": {
                            "app_id": 123456789,
                            "app_secret": "private-tencent-app",
                            "secret_id": "private-tencent-id",
                            "secret_key": "private-tencent-key",
                        },
                        "aliyun": {
                            "access_key_id": "private-aliyun-id",
                            "access_key_secret": "private-aliyun-key",
                            "scene_id": "scene-public",
                            "prefix": "prefix-public",
                        },
                    }
                }
            }
        }
    )
    bootstrap = BootstrapConfigProvider.load(root, app_env="dev", environ={})
    configuration = ConfigProvider(bootstrap, (CaptchaSettings,))
    try:
        settings = configuration.get_config(CaptchaSettings)
        assert settings.enabled and settings.provider == kind
        http = Mock(spec=CaptchaHttpClient)
        provider = (
            TencentCaptchaProvider(settings.tencent, http)
            if kind == "tencent"
            else AliyunCaptchaProvider(settings.aliyun, http)
        )
        data, record = provider.create("password_reset")
        assert record.purpose == "password_reset"
        assert "private-" not in json.dumps(data)
        if kind == "tencent":
            assert data == {"app_id": "123456789"}
        else:
            assert data["scene_id"] == "scene-public" and data["prefix"] == "prefix-public"
        http.post.assert_not_called()
    finally:
        configuration.close()
