import asyncio
import hashlib
import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from framework.starter_cache.public import CacheHandler
from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants

pytestmark = pytest.mark.asyncio(loop_scope="module")
PREFIX = "/admin-api/infra/cache/monitor"


async def seeded_cache(infra_app, admin_client):
    application = infra_app.state.application_context
    with application.execution(), infra_app.state.database.scope():
        async with application.container.get(SecurityService).authorized(
            admin_client.headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            cache = application.container.get(CacheHandler)
            client = cache.get_client(SystemCacheKeyConstants.ROLE)
            key = cache.build_full_key(SystemCacheKeyConstants.ROLE, "cleanup-test")
            ticket = cache.build_full_key(SystemCacheKeyConstants.QR_LOGIN, "cleanup-test")
            foreign = f"__tenant__:t{hashlib.sha256(b'other-tenant').hexdigest()}:system:role:cleanup-test"
            await client.mset({key: "{}", ticket: "{}", foreign: "{}", "custom:keep": "keep"})
            return client, key, ticket, foreign


async def cleanup(admin_client, preset, **extra):
    return (
        await admin_client.post(
            PREFIX + "/cleanup-preset", json={"dbName": "default", "preset": preset, **extra}
        )
    ).json()


async def test_owner_sees_categorized_presets_and_business_cleanup_is_bounded(
    infra_app, admin_client
):
    response = (
        await admin_client.get(PREFIX + "/cleanup-presets", params={"dbName": "default"})
    ).json()
    assert response["code"] == 0, response
    presets = {item["code"]: item for item in response["data"]}
    assert set(presets) == {"business", "authentication", "mq", "jobs"}
    assert presets["business"]["highRisk"] is False
    assert all(presets[code]["highRisk"] for code in ("authentication", "mq", "jobs"))
    client, key, ticket, foreign = await seeded_cache(infra_app, admin_client)
    lease_key = infra_app.state.job.lease.key
    lease_token = await client.get(lease_key)
    response = await cleanup(admin_client, "business")
    assert response["code"] == 0 and response["data"] >= 1, response
    assert await client.get(key) is None
    assert await client.get(ticket) == "{}"
    assert await client.get(foreign) == "{}"
    assert await client.get("custom:keep") == "keep"
    assert await client.get(lease_key) == lease_token
    assert (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()[
        "code"
    ] == 0


@pytest.mark.skipif(
    os.environ.get("DUSHAN_REDIS_FAULT_CONTAINER") is None,
    reason="requires an explicitly selected isolated Redis container",
)
async def test_redis_server_outage_recovers_mq_and_job(
    infra_app, infra_database, admin_client, tmp_path
):
    resources = infra_database[0]
    container = os.environ["DUSHAN_REDIS_FAULT_CONTAINER"]
    assert container == resources["redis_container"] and container.startswith("dushan-unattended-")
    assert Path(tmp_path).resolve().is_relative_to((Path.cwd() / "Temp").resolve())
    config = tmp_path / "docker-cli"
    config.mkdir()

    def linux(path):
        resolved = Path(path).resolve().as_posix()
        return "/mnt/" + resolved[0].lower() + resolved[2:]

    async def docker(action):
        command = [
            "wsl.exe",
            "-d",
            "Ubuntu-24.04",
            "-u",
            "root",
            "--cd",
            linux(Path.cwd()),
            "--exec",
            "env",
            f"TMPDIR={linux(tmp_path)}",
            f"TEMP={linux(tmp_path)}",
            f"TMP={linux(tmp_path)}",
            "docker",
            "--config",
            linux(config),
            action,
            container,
        ]
        await asyncio.to_thread(
            subprocess.run, command, check=True, capture_output=True, timeout=15
        )

    previous = infra_app.state.job.lease
    actors = dict(infra_app.state.mq.actors)
    await docker("pause")
    try:
        async with asyncio.timeout(25):
            while (
                infra_app.state.job.owner
                or not infra_app.state.mq.resources()["recovering_consumers"]
            ):
                await asyncio.sleep(0.05)
    finally:
        await docker("unpause")
    async with asyncio.timeout(25):
        while (
            infra_app.state.job.lease is previous
            or infra_app.state.job.phase != "running"
            or infra_app.state.mq.resources()["recovering_consumers"]
        ):
            await asyncio.sleep(0.05)
    assert not infra_app.state.mq.paused
    assert infra_app.state.mq.actors == actors and all(
        not actor.done() for actor in actors.values()
    )
    assert (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()[
        "code"
    ] == 0


async def test_authentication_cleanup_requires_confirmation_and_preserves_business_cache(
    infra_app, admin_client
):
    client, key, ticket, foreign = await seeded_cache(infra_app, admin_client)
    assert (await cleanup(admin_client, "authentication"))["code"] != 0
    assert await client.get(ticket) == "{}"
    response = await cleanup(admin_client, "authentication", confirmation="CLEAR")
    assert response["code"] == 0, response
    assert await client.get(ticket) is None
    assert await client.get(key) == "{}" and await client.get(foreign) == "{}"
    assert (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()[
        "code"
    ] == 0


async def test_mq_cleanup_is_limited_to_this_application(infra_app, admin_client):
    client, key, ticket, _ = await seeded_cache(infra_app, admin_client)
    response = (
        await admin_client.get(PREFIX + "/cleanup-presets", params={"dbName": "default"})
    ).json()
    preset = next(item for item in response["data"] if item["code"] == "mq")
    owned = preset["patterns"][0].removesuffix("*") + "cleanup-test"
    foreign = "mq:another-application:cleanup-test"
    await client.mset({owned: "test", foreign: "keep"})
    assert (await cleanup(admin_client, "mq"))["code"] != 0
    assert await client.get(owned) == "test"
    response = await cleanup(admin_client, "mq", confirmation="CLEAR")
    assert response["code"] == 0, response
    assert await client.get(owned) is None and await client.get(foreign) == "keep"
    assert await client.get(key) == "{}" and await client.get(ticket) == "{}"


async def test_job_cleanup_reelects_owner_without_deleting_definitions(
    infra_app, infra_database, admin_client
):
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM infra_job WHERE deleted=0")
        before = cursor.fetchone()[0]
    previous = infra_app.state.job.lease
    response = await cleanup(admin_client, "jobs", confirmation="CLEAR")
    assert response["code"] == 0, response
    async with asyncio.timeout(25):
        while infra_app.state.job.lease is previous or infra_app.state.job.phase != "running":
            await asyncio.sleep(0.05)
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM infra_job WHERE deleted=0")
        assert cursor.fetchone()[0] == before


async def test_nonowner_cannot_manage_redis_even_with_legacy_super_role(
    infra_app, infra_database, admin_client
):
    username = "cache" + uuid4().hex[:8]
    created = (
        await admin_client.post(
            "/admin-api/system/user/create",
            json={"username": username, "nickname": "NotOwner", "password": "CacheTest123!"},
        )
    ).json()
    assert created["code"] == 0, created
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "INSERT INTO system_user_role (id,user_id,role_id,tenant_id,creator,updater,create_time,update_time,deleted) VALUES (900000000000000119,%s,10100000040001,'1','test','test',NOW(),NOW(),0)",
            (created["data"],),
        )
    async with AsyncClient(
        transport=ASGITransport(app=infra_app), base_url="http://testserver"
    ) as client:
        login = (
            await client.post(
                "/admin-api/system/auth/login",
                json={"username": username, "password": "CacheTest123!"},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert login["code"] == 0, login
        client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
        for path, params in (("/cleanup-presets", {"dbName": "default"}), ("/db-list", {})):
            assert (await client.get(PREFIX + path, params=params)).json()["code"] != 0
        for preset in ("business", "authentication", "mq", "jobs"):
            assert (await cleanup(client, preset, confirmation="CLEAR"))["code"] != 0
        assert (await client.delete(PREFIX + "/clear-cache-all")).json()["code"] != 0
    assert (await cleanup(admin_client, "business", dbName="not-configured"))["code"] != 0


async def test_owner_retains_full_clear_and_runtime_recovers(infra_app, admin_client):
    client, _, _, foreign = await seeded_cache(infra_app, admin_client)
    previous = infra_app.state.job.lease
    response = (await admin_client.delete(PREFIX + "/clear-cache-all")).json()
    assert response["code"] == 0, response
    assert await client.get(foreign) is None and await client.get("custom:keep") is None
    async with asyncio.timeout(25):
        while (
            infra_app.state.job.lease is previous
            or infra_app.state.job.phase != "running"
            or infra_app.state.mq.resources()["recovering_consumers"]
        ):
            await asyncio.sleep(0.05)
    assert (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()[
        "code"
    ] == 0
