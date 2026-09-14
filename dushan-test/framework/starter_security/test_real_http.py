import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine

from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot

from .providers import metadata, permissions, sessions

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.smoke
@pytest.mark.parametrize("engine", ["uvicorn", "granian"])
def test_real_http_auth_cache_database_and_shutdown(engine, config_dir, tmp_path, security_module):
    target = json.loads(os.environ.get("DUSHAN_SECURITY_TEST_REDIS", "null"))
    if target is None:
        pytest.skip("真实进程验证需要本轮私有 Redis")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    folder = tmp_path / engine
    folder.mkdir()
    url = f"sqlite+aiosqlite:///{(folder / 'security.sqlite').as_posix()}"
    token = OpaqueToken.generate()
    session = LoginSession(
        application_id=engine,
        domain="admin",
        token_digest=OpaqueToken.digest(token),
        session_id="session",
        family_id="family",
        account_id="http-user",
        realm=SecurityRealm.ACCOUNT,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        revoked=False,
        account_enabled=True,
        credential_revision=1,
        current_credential_revision=1,
        authorization_revision="1",
        scopes=frozenset(),
    )
    snapshot = PermissionSnapshot(
        binding=SecurityService.binding(session),
        revision="1",
        permissions=frozenset({"read"}),
        roles=frozenset({"reader"}),
    )

    async def prepare():
        db = create_async_engine(url)
        try:
            async with db.begin() as connection:
                await connection.run_sync(metadata.create_all)
                await connection.execute(
                    insert(sessions).values(
                        digest=session.token_digest, data=session.model_dump(mode="json")
                    )
                )
                await connection.execute(
                    insert(permissions).values(
                        binding=snapshot.binding,
                        revision="1",
                        data=snapshot.model_dump(mode="json"),
                    )
                )
        finally:
            await db.dispose()

    asyncio.run(prepare())
    root = config_dir(
        {
            "server": {"port": port, "reload": False, "engine": engine},
            "banner": {"enabled": False},
            "modules": {
                "packages": ["framework", security_module],
                "enabled": ["framework", security_module],
            },
            "config": {
                "models": {
                    "security": {
                        "enabled": True,
                        "application_id": engine,
                        "permission_cache_enabled": True,
                    },
                    "cache": {"enabled": True, **target, "clients": [{"name": "default", "db": 0}]},
                    "database": {
                        "enabled": True,
                        "health_check_enabled": False,
                        "sources": [
                            dict(
                                name="primary",
                                url=url,
                                role="primary",
                                weight=100,
                                pool=None,
                                tls=None,
                            )
                        ],
                    },
                }
            },
        }
    )
    env = dict(os.environ, DUSHAN_CONFIG_DIR=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    env["PYTHONPATH"] = os.pathsep.join(
        map(
            str,
            [
                ROOT / "dushan-admin-backend",
                ROOT / "dushan-test",
                ROOT / "dushan-test/framework",
                tmp_path,
            ],
        )
    )
    wheel_root = os.environ.get("DUSHAN_SECURITY_WHEEL_ROOT")
    if wheel_root is not None:
        host_root = folder / "host"
        shutil.copytree(
            ROOT / "dushan-admin-backend/server",
            host_root / "server",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "logs", "Temp"),
        )
        env["PYTHONPATH"] = os.pathsep.join(
            map(
                str,
                [
                    wheel_root,
                    host_root,
                    ROOT / "dushan-test",
                    ROOT / "dushan-test/framework",
                    tmp_path,
                ],
            )
        )
    for name in ("TEMP", "TMP", "TMPDIR"):
        env[name] = str(folder)
    with (folder / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-m",
                "starter_security.http_host",
                "--engine",
                engine,
                "--port",
                str(port),
                "--evidence",
                str(folder),
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            **(
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {"start_new_session": True}
            ),
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False
            ) as client:
                deadline = time.monotonic() + 30
                while True:
                    assert process.poll() is None, (folder / "server.log").read_text(
                        encoding="utf-8"
                    )
                    try:
                        if client.get("/health").json()["data"]["status"] == "ready":
                            break
                    except (httpx.NetworkError, httpx.TimeoutException):
                        pass
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
                missing = client.get("/__security_test/protected")
                assert (
                    missing.json()["code"] == 401
                    and missing.headers["www-authenticate"] == "Bearer"
                )
                headers = {"Authorization": "Bearer " + token}
                assert client.get("/__security_test/protected", headers=headers).json() == {
                    "account": "http-user"
                }
                assert client.post("/__security_test/logout", headers=headers).json()["revoked"]
                assert (
                    client.get("/__security_test/protected", headers=headers).json()["code"] == 401
                )
                assert client.post("/__security_test/stop").json()["stopping"]
            process.wait(timeout=15)
            assert process.returncode == 0
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    closed = json.loads((folder / "closed.json").read_text(encoding="utf-8"))
    assert closed == {
        "ready": False,
        "security_released": True,
        "database_released": True,
        "di_released": True,
        "logging_closed": True,
    }
    assert token not in (folder / "server.log").read_text(encoding="utf-8")
    origin = Path(
        json.loads((folder / "origin.json").read_text(encoding="utf-8"))["security"]
    ).resolve()
    expected = Path(wheel_root) if wheel_root is not None else ROOT / "dushan-admin-backend"
    assert origin.is_relative_to(expected.resolve())
