import re
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute, _iter_routes_with_context
from httpx import ASGITransport, AsyncClient

from framework.starter_web.routing.route_policy import RoutePolicy
from module_infra.router import routers

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def create(client, domain, payload):
    result = (await client.post(f"/admin-api/infra/{domain}/create", json=payload)).json()
    assert result["code"] == 0, (domain, result)
    return result["data"]


async def verify_batch(client, app, connection, domain, table, ids):
    path = "/admin-api/infra/" + domain + "/delete-list"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as public:
        denied = (await public.delete(path, params=[("ids", value) for value in ids[:2]])).json()
        assert denied["code"] == 401, (domain, denied)
    for params in ({}, {"ids": ",".join(ids)}, [("ids", ids[0]), ("ids", "invalid")]):
        rejected = (await client.delete(path, params=params)).json()
        assert rejected["code"] == 422, (domain, rejected)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} WHERE id IN (%s,%s,%s) AND deleted=0", ids)
        assert {str(row[0]) for row in cursor.fetchall()} == set(ids)
    deleted = (await client.delete(path, params=[("ids", value) for value in ids[:2]])).json()
    assert deleted["code"] == 0 and deleted["data"] == 2, (domain, deleted)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} WHERE id IN (%s,%s,%s) AND deleted=0", ids)
        assert [str(row[0]) for row in cursor.fetchall()] == ids[2:]


@pytest.mark.parametrize(
    "domain,table", [("config", "infra_config_data"), ("file/config", "infra_file_config")]
)
async def test_crud_and_batch_delete_keep_unselected_rows(
    admin_client, infra_app, infra_database, domain, table
):
    payloads = []
    for _ in range(3):
        key = "http_" + uuid4().hex[:10]
        if domain == "config":
            type_id = await create(
                admin_client,
                "config/type",
                {"name": key, "code": key, "module": "infra", "status": 1},
            )
            payload = {
                "name": key,
                "typeId": type_id,
                "key": key,
                "value": "first",
                "visible": True,
            }
        else:
            payload = {"name": key, "storage": 1, "config": {"domain": "http://testserver"}}
        payloads.append(payload)
    ids = [await create(admin_client, domain, payload) for payload in payloads]
    changed = (
        await admin_client.put(
            f"/admin-api/infra/{domain}/update",
            json={**payloads[0], "id": ids[0], "name": "Updated"},
        )
    ).json()
    assert changed["code"] == 0, changed
    found = (await admin_client.get(f"/admin-api/infra/{domain}/get", params={"id": ids[0]})).json()
    assert found["code"] == 0 and found["data"]["name"] == "Updated", found
    await verify_batch(admin_client, infra_app, infra_database[2], domain, table, ids)


async def test_batch_file_delete_removes_only_requested_content(
    admin_client, infra_app, infra_database
):
    ids, paths, contents = [], [], []
    for index in range(3):
        content = (uuid4().hex + str(index)).encode()
        uploaded = (
            await admin_client.post(
                "/admin-api/infra/file/upload",
                files={"file": (uuid4().hex + ".txt", content, "text/plain")},
                data={"directory": "http-batch"},
            )
        ).json()
        assert uploaded["code"] == 0, uploaded
        paths.append(urlsplit(uploaded["data"]).path)
        contents.append(content)
        with infra_database[2].cursor() as cursor:
            cursor.execute(
                "SELECT id FROM infra_file WHERE url=%s AND deleted=0", (uploaded["data"],)
            )
            ids.append(str(cursor.fetchone()[0]))
    await verify_batch(admin_client, infra_app, infra_database[2], "file", "infra_file", ids)
    for path in paths[:2]:
        missing = await admin_client.get(path)
        assert missing.json()["code"] == 404, missing.text
    retained = await admin_client.get(paths[2])
    assert retained.status_code == 200 and retained.content == contents[2]


async def test_batch_job_delete_updates_persistent_definitions(
    admin_client, infra_app, infra_database
):
    handlers = ["infra.database.health", "infra.database.metrics", "infra.database.backup"]
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM infra_job WHERE handler_name IN (%s,%s,%s) AND deleted=0", handlers
        )
        existing = [str(row[0]) for row in cursor.fetchall()]
    for identifier in existing:
        removed = (
            await admin_client.delete("/admin-api/infra/job/delete", params={"id": identifier})
        ).json()
        assert removed["code"] == 0, removed
    ids = [
        await create(
            admin_client,
            "job",
            {
                "name": "Batch " + handler,
                "handlerName": handler,
                "handlerParam": "{}",
                "cronExpression": "0 0 1 1 *",
                "retryCount": 0,
                "retryInterval": 0,
                "monitorTimeout": 300000,
            },
        )
        for handler in handlers
    ]
    await verify_batch(admin_client, infra_app, infra_database[2], "job", "infra_job", ids)


async def test_config_batch_delete_cannot_remove_foreign_tenant_data(admin_client, infra_database):
    key = "foreign_" + uuid4().hex[:10]
    type_id = await create(
        admin_client, "config/type", {"name": key, "code": key, "module": "infra", "status": 1}
    )
    identifier = await create(
        admin_client,
        "config",
        {"name": key, "typeId": type_id, "key": key, "value": "retained", "visible": True},
    )
    with infra_database[2].cursor() as cursor:
        foreign_type_id = 9000000000000001001
        cursor.execute(
            "INSERT INTO infra_config_type(id,tenant_id,module,name,code,status,creator,updater,create_time,update_time,deleted) SELECT %s,'999',module,name,code,status,creator,updater,create_time,update_time,deleted FROM infra_config_type WHERE id=%s",
            (foreign_type_id, type_id),
        )
        cursor.execute(
            "UPDATE infra_config_data SET tenant_id='999',type_id=%s WHERE id=%s",
            (foreign_type_id, identifier),
        )
    result = (
        await admin_client.delete("/admin-api/infra/config/delete-list", params={"ids": identifier})
    ).json()
    assert result["code"] == 403, result
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT value,deleted FROM infra_config_data WHERE id=%s", (identifier,))
        assert cursor.fetchone() == ("retained", 0)


async def test_all_protected_infra_routes_reject_anonymous(infra_app):
    checked = 0
    async with AsyncClient(
        transport=ASGITransport(app=infra_app), base_url="http://testserver"
    ) as public:
        for router in routers:
            for route, context in _iter_routes_with_context(router.routes):
                if not isinstance(route, APIRoute):
                    continue
                policy = getattr(route.endpoint, RoutePolicy.ATTRIBUTE)
                if not policy.requires_identity:
                    continue
                path = context.path if context else route.path
                url = re.sub(r"\{[^}]+\}", "9223372036854775807", path)
                for method in route.methods:
                    response = (await public.request(method, url, json={})).json()
                    assert response["code"] == 401, (method, path, response)
                    checked += 1
    assert checked > 100
