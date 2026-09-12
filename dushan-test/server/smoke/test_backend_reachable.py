import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from config_factory import ConfigFactory

BACKEND_ROOT = Path(__file__).resolve().parents[3] / "dushan-admin-backend"


@pytest.mark.smoke
@pytest.mark.parametrize("engine", ["uvicorn", "granian"])
def test_real_server_health(engine, config_dir, tmp_path):
    """按双 worker 配置启动，验证就绪、实际输出顺序及横幅不重复。"""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    name = ConfigFactory.values()["server"]["name"]
    root = config_dir(
        {"server": {"name": name, "port": port, "reload": False}, engine: {"workers": 2}}
    )
    env = dict(
        os.environ,
        SERVER_ENV="test",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
    )
    log_path = tmp_path / f"{engine}.log"
    options = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        options["start_new_session"] = True
    with log_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(BACKEND_ROOT / "app.py"),
                "--server",
                engine,
                "--env",
                "test",
                "--config-dir",
                str(root),
            ],
            cwd=BACKEND_ROOT.parent,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            **options,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("服务进程提前退出：" + log_path.read_text(encoding="utf-8"))
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                        payload = json.load(response)
                        assert response.status == 200
                        assert payload["data"]["status"] == "ready"
                        break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.1)
            else:
                pytest.fail("等待健康接口超时：" + log_path.read_text(encoding="utf-8"))
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)

    text = log_path.read_text(encoding="utf-8")
    logo = (
        (BACKEND_ROOT / "framework/starter_web/banner/assets/logo.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert text.startswith(logo + "\n")
    assert text.count(logo) == 1
    worship = (
        (BACKEND_ROOT / "framework/starter_web/banner/assets/worship.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert text.count(worship) == 1
    engine_message = "Starting granian" if engine == "granian" else "Started parent process"
    assert text.index(worship) < text.index(engine_message)
    before_engine = text[: text.index(engine_message)]
    assert all(label not in before_engine for label in ("引擎：", "环境：", "监听地址："))
    assert "应用初始化完成：dushan-ai-native" in text
    assert text.index("服务已就绪") < text.index("应用初始化完成：dushan-ai-native")
    for segment in text.split("应用初始化完成：")[1:]:
        summary = segment.split("监听地址：", 1)[0]
        assert summary.count("引擎：") == 1 and summary.count("环境：") == 1
