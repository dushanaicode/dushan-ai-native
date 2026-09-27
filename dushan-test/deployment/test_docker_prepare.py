import importlib.util
import json
from pathlib import Path

import bcrypt
import pytest
import yaml

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.vo.auth_login_req_vo import AuthLoginReqVO
from server.config.application_settings import ApplicationSettings

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_docker_prepare", ROOT / "docker/prepare.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


@pytest.fixture
def prepared(tmp_path):
    output = tmp_path / "runtime"
    PREPARE.Prepare.prepare(output, "https://admin.example.com:18443")
    return output


def test_generated_config_matches_backend_contracts(prepared):
    provider = BootstrapConfigProvider.load(prepared / "application", app_env="prod", environ={})
    application = provider.get_config(ApplicationSettings)
    assert application.granian.workers == 1
    assert set(application.modules.enabled) == {"framework", "system", "infra"}
    assert not application.server.docs_enabled
    models = application.config.models
    database = DatabaseSettings.model_validate(models["database"])
    assert database.enabled
    assert len(database.sources) == 1
    for key, model in (
        ("cache", CacheSettings),
        ("job", JobSettings),
        ("mq", MQSettings),
        ("websocket", WebSocketSettings),
    ):
        assert model.model_validate(models[key]).enabled
    system = SystemSettings.model_validate(models["system"])
    assert system.refresh_cookie_secure
    assert system.allowed_origins == ("https://admin.example.com:18443",)


def test_credentials_seed_and_storage_are_consistent(prepared):
    credentials = json.loads((prepared / "credentials.json").read_text())
    config = yaml.safe_load((prepared / "application/application.yaml").read_text(encoding="utf-8"))
    assert credentials["redis-password"] == config["config"]["models"]["cache"]["password"]
    seed = (prepared / "mysql-init/999_deployment_credentials.sql").read_text()
    password_hash = seed.splitlines()[1].split("password='")[1].split("'")[0]
    AuthLoginReqVO(username="admin", password=credentials["admin"])
    assert len(credentials["vendor-password"]) <= 32
    assert bcrypt.checkpw(credentials["admin"].encode(), password_hash.encode())
    assert not bcrypt.checkpw(b"admin123", password_hash.encode())
    assert "status=0" in seed
    assert "status=1 WHERE id=10100000010001" in seed
    assert len(list((prepared / "mysql-init").glob("*.sql"))) > 8


def test_repeat_preparation_does_not_replace_existing_secrets(prepared):
    before = (prepared / "credentials.json").read_bytes()
    with pytest.raises(FileExistsError):
        PREPARE.Prepare.prepare(prepared, "http://localhost:18080")
    assert (prepared / "credentials.json").read_bytes() == before


@pytest.mark.parametrize(
    "origin",
    [
        "http://192.168.1.10:18080",
        "https://admin.example.com/path",
        "https://user:password@example.com",
        "https://example.com\n",
        "https://example.com:0",
    ],
)
def test_invalid_origin_does_not_create_files(tmp_path, origin):
    output = tmp_path / "runtime"
    with pytest.raises(ValueError):
        PREPARE.Prepare.prepare(output, origin)
    assert not output.exists()


def test_preparation_rejects_path_outside_cwd_temp():
    with pytest.raises(ValueError, match="Temp"):
        PREPARE.Prepare.prepare(ROOT / "docker-invalid-runtime", "http://localhost:18080")
