"""启动参数、子进程边界和退出码验证。"""

import subprocess

import pytest

import app as entry
from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings
from server.launcher.engine_parser import parse_server_arguments
from server.launcher.granian_launcher import build_granian_cmd
from server.launcher.uvicorn_launcher import build_uvicorn_cmd


def test_default_engine_is_granian():
    assert parse_server_arguments([]).server == "granian"


@pytest.mark.parametrize(
    "builder,engine",
    [
        (build_granian_cmd, GranianSettings(workers=3)),
        (build_uvicorn_cmd, UvicornSettings(workers=3)),
    ],
)
def test_reload_uses_one_worker(builder, engine):
    command = builder(ServerSettings(reload=True), engine)
    assert command[command.index("--workers") + 1] == "1"
    assert "--reload" in command
    assert "-B" in command


def test_production_engine_parameters_are_explicit():
    server = ServerSettings(env="prod", docs_enabled=False)
    granian = build_granian_cmd(server, GranianSettings(workers=2, threads=3))
    uvicorn = build_uvicorn_cmd(server, UvicornSettings(workers=2))
    assert granian[granian.index("--runtime-threads") + 1] == "3"
    assert uvicorn[uvicorn.index("--workers") + 1] == "2"
    assert "--no-proxy-headers" in uvicorn
    assert uvicorn[uvicorn.index("--lifespan") + 1] == "on"


def test_entry_sends_validated_configuration_to_child(config_dir, monkeypatch):
    root = config_dir({"SERVER_PORT": 40123})
    monkeypatch.setenv("UVICORN_RELOAD", "true")
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
    root = config_dir({"SERVER_PORT": 0})
    monkeypatch.setattr(
        entry.subprocess, "run", lambda *a, **k: pytest.fail("非法配置不应启动子进程")
    )
    assert entry.run_server(["--config-dir", str(root)]) == 2


def test_child_failure_is_not_reported_as_success(config_dir, monkeypatch):
    monkeypatch.setattr(
        entry.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 9)
    )
    assert entry.run_server(["--config-dir", str(config_dir())]) == 9
