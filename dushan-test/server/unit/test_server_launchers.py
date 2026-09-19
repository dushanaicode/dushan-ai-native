import subprocess
from importlib.resources import files

import pytest

import app as entry
from fixtures.config_factory import ConfigFactory
from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings
from server.enums.server_engine_enum import ServerEngineEnum
from server.launcher.engine_parser import parse_server_arguments
from server.launcher.granian_launcher import build_granian_cmd
from server.launcher.uvicorn_launcher import build_uvicorn_cmd


def test_default_engine_is_granian():
    assert parse_server_arguments([]).server is None
    assert ConfigFactory.build(ServerSettings, "server").engine is ServerEngineEnum.GRANIAN
    assert ConfigFactory.build(ServerSettings, "server").name == "dushan-ai-native"


@pytest.mark.parametrize(
    "builder,engine",
    [
        (build_granian_cmd, ConfigFactory.build(GranianSettings, "granian", workers=3)),
        (build_uvicorn_cmd, ConfigFactory.build(UvicornSettings, "uvicorn", workers=3)),
    ],
)
def test_reload_uses_one_worker(builder, engine):
    command = builder(ConfigFactory.build(ServerSettings, "server", reload=True), engine)
    assert command[command.index("--workers") + 1] == "1"
    assert "--reload" in command
    assert "-B" in command


def test_production_engine_parameters_are_explicit():
    server = ConfigFactory.build(ServerSettings, "server", env="prod", docs_enabled=False)
    granian = build_granian_cmd(
        server, ConfigFactory.build(GranianSettings, "granian", workers=2, threads=3)
    )
    uvicorn = build_uvicorn_cmd(server, ConfigFactory.build(UvicornSettings, "uvicorn", workers=2))
    assert granian[granian.index("--runtime-threads") + 1] == "3"
    assert uvicorn[uvicorn.index("--workers") + 1] == "2"
    assert "--no-proxy-headers" in uvicorn
    assert uvicorn[uvicorn.index("--lifespan") + 1] == "on"


def test_entry_sends_validated_configuration_to_child(config_dir, monkeypatch):
    root = config_dir({"server": {"port": 40123}})
    monkeypatch.setenv("UVICORN_WORKERS", "3")
    monkeypatch.setenv("GRANIAN_WORKERS", "2")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", run)
    assert (
        entry.run_server(["--server", "uvicorn", "--env", "test", "--config-dir", str(root)]) == 0
    )
    command, kwargs = calls[0]
    assert command[command.index("--port") + 1] == "40123"
    assert kwargs["cwd"] == entry.BACKEND_ROOT
    assert kwargs["env"]["DUSHAN_CONFIG_DIR"] == str(root.resolve())
    assert kwargs["env"]["SERVER_ENV"] == "test"
    assert not any(key.startswith(("UVICORN_", "GRANIAN_")) for key in kwargs["env"])
    assert kwargs.get("shell", False) is False


def test_invalid_config_does_not_create_a_process(config_dir, monkeypatch):
    root = config_dir({"server": {"port": 0}})
    monkeypatch.setattr(
        entry.subprocess, "run", lambda *a, **k: pytest.fail("非法配置不应启动子进程")
    )
    assert entry.run_server(["--config-dir", str(root)]) == 2


@pytest.mark.parametrize("engine", ["granian", "uvicorn"])
@pytest.mark.parametrize("enabled", [False, True])
def test_launcher_prints_full_banner_without_early_runtime_details(
    config_dir, monkeypatch, capsys, engine, enabled
):
    """引擎启动前只输出完整图案，运行信息留到成功初始化后。"""
    root = config_dir(
        {
            "banner": {"enabled": enabled, "show_worship": True},
            "log": {"console_level": "NONE"},
        }
    )
    logo = (
        files("framework.starter_web.banner")
        .joinpath("assets/logo.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    calls = []

    def run(command, **kwargs):
        output = capsys.readouterr().out
        assert all(
            label not in output for label in ("引擎：", "环境：", "监听地址：", "应用初始化完成")
        )
        if enabled:
            assert output.startswith(logo + "\n")
            assert output.count(logo) == 1
            assert "_ooOoo_" in output
        else:
            assert output == ""
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", run)
    assert entry.run_server(["--server", engine, "--config-dir", str(root)]) == 0
    assert len(calls) == 1


def test_child_failure_is_not_reported_as_success(config_dir, monkeypatch):
    monkeypatch.setattr(
        entry.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 9)
    )
    assert entry.run_server(["--config-dir", str(config_dir())]) == 9


@pytest.mark.parametrize(
    "cli,environment,expected",
    [
        ([], None, "uvicorn"),
        ([], "granian", "granian"),
        (["--server", "uvicorn"], "granian", "uvicorn"),
    ],
)
def test_engine_default_comes_from_yaml_and_explicit_overrides_win(
    config_dir, monkeypatch, cli, environment, expected
):
    """引擎选择默认读取 YAML，环境变量和命令行的覆盖结果传给工作进程。"""
    root = config_dir({"server": {"engine": "uvicorn"}})
    if environment is None:
        monkeypatch.delenv("SERVER_ENGINE", raising=False)
    else:
        monkeypatch.setenv("SERVER_ENGINE", environment)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", run)
    assert entry.run_server(["--config-dir", str(root), *cli]) == 0
    command, kwargs = calls[0]
    assert command[command.index("-m") + 1] == expected
    assert kwargs["env"]["SERVER_ENGINE"] == expected
