import asyncio
import json
import os
import socket
import subprocess
import sys
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import yaml
from redis.asyncio import Redis

import framework
import server
from fixtures.config_factory import ConfigFactory
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession
from starter_websocket.provider_source import SOURCE

ROOT = Path(__file__).resolve().parents[3]
ORIGIN = "https://ws-tests.example"


class SocketCase(SimpleNamespace):
    async def crash(self):
        self.process.expected_crash = True
        self.process.terminate()
        await asyncio.to_thread(self.process.wait, 10)

    async def ticket(self, identity=None, *, seconds=30):
        identity = self.identity if identity is None else identity
        ticket = OpaqueToken.generate()
        await self.redis.set(
            self.prefix + ":ticket:" + OpaqueToken.digest(ticket), identity.token_digest, ex=seconds
        )
        return ticket

    def url(self, ticket, *, audience="test"):
        return f"ws://127.0.0.1:{self.port}/api/ws?ticket={ticket}&audience={audience}"

    async def save(self, identity):
        await self.redis.set(
            self.prefix + ":session:" + identity.token_digest, identity.model_dump_json(), ex=600
        )

    async def issue(
        self, *, scopes=frozenset({"read", "send"}), tenant="1", member="m1", **changes
    ):
        token = OpaqueToken.generate()
        authority = {
            "realm": SecurityRealm.PLATFORM,
            "platform_operator_id": uuid4().hex,
            "account_id": uuid4().hex,
        }
        if self.tenant_mode:
            authority = dict(
                realm=SecurityRealm.TENANT,
                account_id="account-" + member,
                tenant_id=tenant,
                membership_id=member,
                authority_tenant_id=tenant,
                authority_membership_id=member,
                access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
                dept_id="d1",
            )
        identity = LoginSession(
            application_id="dushan-ai-native",
            domain="admin",
            token_digest=OpaqueToken.digest(token),
            session_id=uuid4().hex,
            family_id=uuid4().hex,
            **authority,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision="1",
            scopes=scopes,
        ).model_copy(update=changes)
        await self.save(identity)
        return token, identity

    async def state(self):
        response = await self.http.get("/api/ws-test/state")
        response.raise_for_status()
        value = response.json()
        assert "pid" in value, value
        return value

    async def wait_state(self, predicate, *, seconds=8):
        async with asyncio.timeout(seconds):
            while True:
                value = await self.state()
                if predicate(value):
                    return value
                await asyncio.sleep(0.02)


@pytest.fixture
def ws_engine(request):
    return getattr(request, "param", "uvicorn")


@pytest.fixture
def ws_options(request):
    return getattr(request, "param", {})


@pytest.fixture
def ws_parallel(request):
    return getattr(request, "param", False)


@pytest.fixture
def ws_database_target(request):
    return getattr(request, "param", None)


@pytest.fixture
async def ws_sql_feature(ws_database_target, tmp_path, module_package):
    if ws_database_target is None:
        yield None
    else:
        from starter_websocket.sql_feature import sql_feature

        async with sql_feature(ws_database_target, tmp_path, module_package) as feature:
            yield feature


@pytest.fixture
async def socket_case(ws_engine, ws_options, tmp_path, module_package, ws_sql_feature, ws_parallel):
    if "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("真实 Redis 实例未配置")
    namespace = "w" + uuid4().hex[:10] if ws_sql_feature is None else ws_sql_feature.namespace
    package = "socket_case_" + namespace
    source = SOURCE if ws_sql_feature is None else ws_sql_feature.source
    if ws_parallel:
        source = source.replace("policy=read))", "policy=read,parallel=True))")
    module_package(package, scan_roots=(".",), files={"components.py": source})
    redis = Redis(
        host="127.0.0.1", port=int(os.environ["DUSHAN_DP_REDIS_PORT"]), decode_responses=True
    )
    case = SocketCase(
        redis=redis, prefix="ws-tests:" + namespace, tenant_mode=ws_sql_feature is not None
    )
    case.token, case.identity = await case.issue()
    processes = []
    started = set()
    async with AsyncExitStack() as stack:

        async def start(engine=ws_engine):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            folder = tmp_path / (engine + "_" + str(port))
            folder.mkdir()
            values = ConfigFactory.values()
            ConfigFactory.merge(
                values,
                {
                    "server": {
                        "host": "127.0.0.1",
                        "port": port,
                        "reload": False,
                        "engine": engine,
                    },
                    "banner": {"enabled": False},
                    "log": {"enable_file_overall": False},
                    "modules": {
                        "packages": ["framework", package],
                        "enabled": ["framework", package],
                    },
                    "config": {
                        "models": {
                            "security": {"enabled": True},
                            "cache": {
                                "enabled": True,
                                "port": int(os.environ["DUSHAN_DP_REDIS_PORT"]),
                            },
                            "websocket": {
                                "enabled": True,
                                "namespace": namespace,
                                "allowed_origins": [ORIGIN],
                                "signing_secret": "ws-tests-only-instance-delivery-signing-secret",
                                "shutdown_seconds": 0.2,
                                **ws_options,
                            },
                        }
                    },
                },
            )
            if ws_sql_feature is not None:
                ConfigFactory.merge(
                    values,
                    {
                        "modules": {
                            "packages": ["framework", package, ws_sql_feature.package],
                            "enabled": ["framework", package, ws_sql_feature.package],
                        },
                        "config": {"models": ws_sql_feature.models},
                    },
                )
            (folder / "application.yaml").write_text(
                yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
            )
            env = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONUTF8="1",
                PYTHONPATH=os.pathsep.join(
                    dict.fromkeys(
                        (
                            str(Path(framework.__file__).resolve().parents[1]),
                            str(Path(server.__file__).resolve().parents[1]),
                            str(ROOT / "dushan-test"),
                            str(tmp_path),
                        )
                    )
                ),
            )
            for name in ("TEMP", "TMP", "TMPDIR"):
                env[name] = str(folder)
            worker = Path(__file__).parent / "worker.py"
            paths = [
                *env["PYTHONPATH"].split(os.pathsep),
                str(Path(pytest.__file__).resolve().parents[1]),
            ]
            bootstrap = folder / "worker_bootstrap.py"
            bootstrap.write_text(
                "import runpy, sys\n"
                + f"sys.path[:0] = {paths!r}\n"
                + f"sys.argv = [{str(worker)!r}, *sys.argv[1:]]\n"
                + f"runpy.run_path({str(worker)!r}, run_name='__main__')\n",
                encoding="utf-8",
            )
            output = (folder / "server.log").open("w", encoding="utf-8")
            options = (
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-X",
                    "utf8",
                    str(bootstrap),
                    "--engine",
                    engine,
                    "--port",
                    str(port),
                    "--config",
                    str(folder),
                    "--evidence",
                    str(folder),
                ],
                cwd=ROOT,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                **options,
            )
            processes.append((process, output, folder, port))
            http = await stack.enter_async_context(
                httpx.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}",
                    headers={"Authorization": "Bearer " + case.token},
                    timeout=10,
                    trust_env=False,
                )
            )
            async with asyncio.timeout(20):
                while True:
                    assert process.poll() is None, (folder / "server.log").read_text(
                        encoding="utf-8"
                    )
                    try:
                        if (await http.get("/health")).json()["data"]["status"] == "ready":
                            break
                    except (httpx.NetworkError, httpx.TimeoutException):
                        pass
                    await asyncio.sleep(0.05)
            started.add(process.pid)
            return SocketCase(
                redis=redis,
                prefix=case.prefix,
                token=case.token,
                identity=case.identity,
                http=http,
                port=port,
                folder=folder,
                process=process,
                tenant_mode=case.tenant_mode,
                sql=ws_sql_feature,
            )

        try:
            first = await start()
            first.peer = start
            yield first
        finally:
            failures = []
            for process, output, folder, port in reversed(processes):
                try:
                    if process.poll() is None:
                        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
                            await client.post(f"http://127.0.0.1:{port}/__ws_stop")
                        await asyncio.to_thread(process.wait, 15)
                    if process.pid in started and not getattr(process, "expected_crash", False):
                        assert process.returncode == 0, (folder / "server.log").read_text(
                            encoding="utf-8"
                        )
                        closed = json.loads((folder / "closed.json").read_text(encoding="utf-8"))
                        assert closed["di_released"] and not closed["ready"]
                        assert (
                            Path(closed["framework_root"]).resolve()
                            == Path(framework.__file__).resolve().parent
                        )
                        assert bool(closed["stop_errors"]) is bool(
                            getattr(process, "expected_close_failure", False)
                        )
                        assert (
                            closed["websocket"]["connections"]
                            == closed["websocket"]["active_handlers"]
                            == 0
                        )
                except Exception as error:
                    failures.append(error)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        await asyncio.to_thread(process.wait, 10)
                    output.close()
            await redis.aclose()
            if failures:
                raise ExceptionGroup("WebSocket 测试进程关闭失败", failures)
