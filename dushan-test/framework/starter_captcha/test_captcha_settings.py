import json

import pytest

from fixtures.config_factory import ConfigFactory
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider

pytestmark = pytest.mark.unit


class TestCaptchaSettings:
    CREDENTIALS = {
        "aliyun": {"access_key_id": "fixture-access-id", "access_key_secret": "fixture-access-key"},
        "tencent": {
            "app_secret": "fixture-app-secret",
            "secret_id": "fixture-secret-id",
            "secret_key": "fixture-secret-key",
        },
    }

    @pytest.mark.parametrize("source", ["memory", "external", "file"])
    def test_untrusted_sources_cannot_override_startup_settings(self, config_dir, tmp_path, source):
        """内存、外部快照和附加文件不能覆盖验证码凭据或启动开关。"""
        injection = {"config": {"models": {"captcha": {"enabled": True, **self.CREDENTIALS}}}}
        options = {"reload_enabled": True}
        if source == "file":
            path = tmp_path / "captcha-overrides.json"
            path.write_text(json.dumps(injection), encoding="utf-8")
            options["files"] = [{"path": str(path), "required": True}]
        bootstrap = BootstrapConfigProvider.load(config_dir({"config": options}), environ={})
        current = ConfigProvider(
            bootstrap,
            [CaptchaSettings],
            external_values=injection if source == "external" else None,
        )
        try:
            if source == "memory":
                current.replace_memory(injection)
            expected = CaptchaSettings.model_validate(
                ConfigFactory.values()["config"]["models"]["captcha"]
            )
            assert current.get_config(CaptchaSettings) == expected
            assert set(current.get_sources(CaptchaSettings).values()) == {"application.yaml"}
        finally:
            current.close()

    @pytest.mark.parametrize("source", ["yaml", "environment"])
    def test_trusted_sources_supply_cloud_credentials(self, config_dir, source):
        """启动 YAML 与环境变量均能提供两家云验证码的全部凭据。"""
        values = {"config": {"models": {"captcha": self.CREDENTIALS}}} if source == "yaml" else {}
        environ = (
            {
                f"CAPTCHA_{provider.upper()}_{field.upper()}": value
                for provider, credentials in self.CREDENTIALS.items()
                for field, value in credentials.items()
            }
            if source == "environment"
            else {}
        )
        current = ConfigProvider(
            BootstrapConfigProvider.load(config_dir(values), environ=environ), [CaptchaSettings]
        )
        try:
            settings = current.get_config(CaptchaSettings)
            origins = current.get_sources(CaptchaSettings)
            for provider, credentials in self.CREDENTIALS.items():
                for field, value in credentials.items():
                    assert getattr(getattr(settings, provider), field).get_secret_value() == value
                    expected_origin = (
                        f"环境变量 CAPTCHA_{provider.upper()}_{field.upper()}"
                        if source == "environment"
                        else "application.yaml"
                    )
                    assert origins[f"{provider}.{field}"] == expected_origin
        finally:
            current.close()
