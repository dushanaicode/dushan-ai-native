import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from fixtures.public_web_app import create_public_app
from server.routing.application_health import ApplicationHealth

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT.parent / "dushan-admin-backend"


@pytest.mark.parametrize("bad_default", ["missing", "invalid_yaml", "invalid_environment"])
def test_factory_import_does_not_load_default_configuration(config_dir, tmp_path, bad_default):
    selected = config_dir({"server": {"name": "explicit-factory", "port": 41234}})
    default = tmp_path / "invalid-default"
    if bad_default != "missing":
        default.mkdir()
        (default / "application.yaml").write_text(
            "server: ["
            if bad_default == "invalid_yaml"
            else (selected / "application.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    env = dict(
        os.environ,
        DUSHAN_CONFIG_DIR=str(default),
        SERVER_ENV="not-an-environment" if bad_default == "invalid_environment" else "test",
        PYTHONPATH=str(BACKEND),
    )
    code = """
import sys
from pathlib import Path
import server.starter_server as factory
assert not hasattr(factory, "app")
assert "server.asgi" not in sys.modules
first = factory.StarterServer.create_app(base_dir=Path(sys.argv[1]), app_env="test", environ={})
second = factory.StarterServer.create_app(base_dir=Path(sys.argv[1]), app_env="test", environ={})
assert first is not second and first.state.bootstrap is not second.state.bootstrap
assert first.title == "explicit-factory" and first.state.bootstrap.settings.port == 41234
assert first.state.application_context is None and second.state.application_context is None
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(selected)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


async def test_disabled_components_are_not_probed(config_dir, monkeypatch):
    class ForbiddenProbe:
        @property
        def is_ready(self):
            pytest.fail("关闭的组件不应被探测")

    app = create_public_app(base_dir=config_dir(), environ={})
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["data"]["components"] == {"bootstrap": "ready"}
        with monkeypatch.context() as patch:
            for name in ("database", "cache", "job", "mq", "websocket"):
                patch.setattr(app.state, name, ForbiddenProbe())
            assert await ApplicationHealth.check(app.state.bootstrap) == {"bootstrap": True}
