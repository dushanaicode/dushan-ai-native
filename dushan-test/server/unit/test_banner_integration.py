import pytest
from fastapi.testclient import TestClient

from fixtures.config_factory import ConfigFactory
from fixtures.public_web_app import create_public_app
from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from server.bootstrap.bootstrapper import BootstrapError
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS

pytestmark = pytest.mark.unit


def test_app_initialization_prints_summary_without_repeating_logo(config_dir, monkeypatch):
    events = []

    def start(self):
        pytest.fail("应用工作进程不应重复打印启动器横幅")

    async def complete(self, info):
        assert application.state.bootstrap.logging_starter.initialized
        assert application.state.bootstrap.exception_handler.translator is not None
        assert application.state.bootstrap.ready
        events.append(info)

    monkeypatch.setattr(BannerApplicationRunner, "print_startup_banner", start)
    monkeypatch.setattr(BannerApplicationRunner, "print_startup_complete", complete)
    application = create_public_app(
        base_dir=config_dir(), environ={"SERVER_VERSION": "2.0", "BANNER_AUTHOR": "Native"}
    )
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
    assert len(events) == 1
    # 启用模块随 application.yaml 的 modules.enabled 变化，这里比对配置而不是写死清单。
    enabled = frozenset(ConfigFactory.values()["modules"]["enabled"])
    assert events[0].version == "2.0" and frozenset(events[0].enabled_modules) == enabled
    assert application.state.bootstrap.config_sources["banner.author"] == "环境变量 BANNER_AUTHOR"
    assert all(step.name != "启动信息" for step in APP_BOOTSTRAP_STEPS)


def test_project_name_and_runtime_details_are_printed_once_at_completion(config_dir, capsys):
    name = ConfigFactory.values()["server"]["name"]
    assert name == "dushan-ai-native"
    app = create_public_app(base_dir=config_dir({"server": {"name": name}}), environ={})
    with TestClient(app) as client:
        # 启动摘要在接收请求前结束；之后正常产生的访问日志不属于摘要。
        output = capsys.readouterr().out
        assert output.count("应用初始化完成：dushan-ai-native") == 1
        assert all(output.count(label) == 1 for label in ("引擎：", "环境：", "监听地址："))
        assert output.splitlines()[-3].startswith("引擎：")
        assert output.splitlines()[-2].startswith("环境：")
        assert output.splitlines()[-1].startswith("监听地址：")
        assert client.get("/openapi.json").json()["info"]["title"] == name


def test_startup_failure_does_not_emit_completion_information(config_dir, monkeypatch):
    completed = []

    async def complete(self, info):
        completed.append(info)

    monkeypatch.setattr(BannerApplicationRunner, "print_startup_complete", complete)
    app = create_public_app(
        base_dir=config_dir({"i18n": {"required_message_keys": ["missing.required"]}}), environ={}
    )
    with pytest.raises(BootstrapError), TestClient(app):
        pass
    assert completed == [] and app.state.bootstrap.ready is False


def test_production_banner_reports_documentation_disabled(config_dir, capsys):
    app = create_public_app(
        base_dir=config_dir(prod={"server": {"docs_enabled": False}}),
        app_env="prod",
        environ={},
    )
    with TestClient(app):
        pass
    summary = capsys.readouterr().out
    assert "应用初始化完成" in summary
    assert "接口文档：已关闭" in summary
    assert "Swagger" not in summary and "ReDoc" not in summary
