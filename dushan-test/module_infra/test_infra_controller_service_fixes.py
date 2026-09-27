from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi.routing import _iter_routes_with_context

from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_infra.api.file.file_api import FileApi
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.service.file.file_config_service import FileConfigService
from module_infra.service.file.file_service import FileService


def test_infra_routes_import():
    from module_infra.router import routers

    paths = {
        context.path
        for router in routers
        for route, context in _iter_routes_with_context(router.routes)
    }
    assert "/admin-api/infra/file/delete-by-keys" in paths
    assert not any(path.startswith("/weapp-api/infra") for path in paths)


@pytest.mark.asyncio(loop_scope="module")
async def test_system_and_infra_real_app_routes_and_openapi(infra_app, admin_client):
    paths = infra_app.openapi()["paths"]
    assert "/admin-api/system/auth/login" in paths
    assert "/admin-api/infra/file/delete-by-keys" in paths
    assert not any(path.startswith("/weapp-api/infra") for path in paths)
    parameters = paths["/admin-api/infra/file/delete-by-keys"]["delete"]["parameters"]
    keys = next(p for p in parameters if p["name"] == "keys")
    assert keys["required"] is True
    assert keys["schema"]["type"] == "array"
    assert keys["schema"]["items"]["type"] == "string"
    assert keys["schema"]["minItems"] == 1


async def config(client):
    result = (
        await client.post(
            "/admin-api/infra/file/config/create",
            json={"name": uuid4().hex, "storage": 1, "config": {"domain": "http://testserver"}},
        )
    ).json()
    assert result["code"] == 0, result
    return int(result["data"])


@asynccontextmanager
async def services(app, client):
    application = app.state.application_context
    with application.execution(), app.state.database.scope():
        async with application.container.get(SecurityService).authorized(
            client.headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            yield application.container


@pytest.mark.asyncio(loop_scope="module")
async def test_batch_keys_preserve_comma_whitespace_and_repeated_query(
    admin_client, infra_app, infra_database
):
    identifier = await config(admin_client)
    keys = ["a,b.txt", "a", "b.txt", " leading-and-trailing ", "one.txt", "two.txt"]
    async with services(infra_app, admin_client) as container:
        service = container.get(FileService)
        for key in keys:
            await service.create_file(
                content=key.encode(), name=key, path=key, config_id=identifier
            )
    for selected in ([keys[0]], [keys[3]], keys[4:]):
        result = (
            await admin_client.delete(
                "/admin-api/infra/file/delete-by-keys",
                params=[("configId", str(identifier)), *(("keys", key) for key in selected)],
            )
        ).json()
        assert result["code"] == 0 and result["data"] == len(selected), result
    with infra_database[2].cursor() as cursor:
        for table, field in (("infra_file", "storage_path"), ("infra_file_content", "path")):
            cursor.execute(
                f"SELECT {field} FROM {table} WHERE config_id=%s AND deleted=0", (identifier,)
            )
            assert {row[0] for row in cursor.fetchall()} == {"a", "b.txt"}
    for params in (
        {"configId": str(identifier)},
        {"configId": str(identifier), "keys": []},
        {"configId": str(identifier), "keys": [""]},
    ):
        result = (
            await admin_client.delete("/admin-api/infra/file/delete-by-keys", params=params)
        ).json()
        assert result["code"] == 422, result


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("operation", ["delete", "rename", "path_api"])
async def test_file_identity_includes_configuration(
    operation, admin_client, infra_app, infra_database
):
    identifiers = [await config(admin_client), await config(admin_client)]
    key = "same.txt"
    async with services(infra_app, admin_client) as container:
        service = container.get(FileService)
        for identifier in identifiers:
            await service.create_file(
                content=str(identifier).encode(), name=key, path=key, config_id=identifier
            )
        if operation == "path_api":
            api = container.get(FileApi)
            assert await api.delete_file_by_storage_path(identifiers[0], key) is True
            assert await api.delete_file_by_storage_path(identifiers[0], "missing.txt") is False
        elif operation == "delete":
            await service.delete_by_key(identifiers[0], key)
        else:
            await service.rename_object(identifiers[0], key, "changed.txt")
        clients = container.get(FileConfigService)
        other = await clients.get_file_client(identifiers[1])
        assert await other.get_content(key) == str(identifiers[1]).encode()
        selected = await clients.get_file_client(identifiers[0])
        if operation == "rename":
            assert await selected.get_content("changed.txt") == str(identifiers[0]).encode()
        with pytest.raises(FileNotFoundError):
            await selected.get_content(key)
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT config_id,storage_path FROM infra_file WHERE config_id IN (%s,%s) AND deleted=0",
            identifiers,
        )
        expected = {(identifiers[1], key)}
        if operation == "rename":
            expected.add((identifiers[0], "changed.txt"))
        assert set(cursor.fetchall()) == expected


@pytest.mark.asyncio(loop_scope="module")
async def test_unregistered_objects_and_storage_failure(
    admin_client, infra_app, infra_database, monkeypatch
):
    identifier = await config(admin_client)
    async with services(infra_app, admin_client) as container:
        service = container.get(FileService)
        client = await container.get(FileConfigService).get_file_client(identifier)
        await client.upload("unregistered.txt", b"raw", "text/plain")
        await service.rename_object(identifier, "unregistered.txt", "renamed.txt")
        assert await client.get_content("renamed.txt") == b"raw"
        await service.delete_by_key(identifier, "renamed.txt")
        with pytest.raises(FileNotFoundError):
            await client.get_content("renamed.txt")
        await service.create_file(
            content=b"keep", name="keep.txt", path="keep.txt", config_id=identifier
        )

        async def fail(*args):
            raise OSError("fixture storage failure")

        monkeypatch.setattr(client, "delete", fail)
        with pytest.raises(OSError, match="fixture storage failure"):
            await service.delete_by_key(identifier, "keep.txt")
        monkeypatch.setattr(client, "rename", fail)
        with pytest.raises(OSError, match="fixture storage failure"):
            await service.rename_object(identifier, "keep.txt", "lost.txt")
        assert await client.get_content("keep.txt") == b"keep"
        assert (
            await container.get(FileMapper).select_by_storage_path(identifier, "keep.txt")
        ).name == "keep.txt"


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("reverse", [False, True])
async def test_listing_uses_complete_key_and_allows_missing_metadata(
    reverse, admin_client, infra_app
):
    identifier = await config(admin_client)
    async with services(infra_app, admin_client) as container:
        service = container.get(FileService)
        rows = [
            ("x.txt", "Root name.txt", "text/plain"),
            ("dir/x.txt", "Nested name.json", "application/json"),
        ]
        for key, name, mime in reversed(rows) if reverse else rows:
            await service.create_file(
                content=b"content", name=name, path=key, type_hint=mime, config_id=identifier
            )
        client = await container.get(FileConfigService).get_file_client(identifier)
        await client.upload("orphan.txt", b"orphan", "text/plain")
        listed = await service.list_objects(identifier, "", "")
        found = {item.key: (item.name, item.type) for item in listed.objects}
        assert found["x.txt"] == ("Root name.txt", "text/plain")
        assert found["dir/x.txt"] == ("Nested name.json", "application/json")
        assert found["orphan.txt"] == ("orphan.txt", "text/plain")


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "path, code", [("job", 1001001000), ("job/log", 404), ("config/type", 1001010004)]
)
async def test_missing_details_are_business_results(path, code, admin_client):
    result = (
        await admin_client.get(f"/admin-api/infra/{path}/get", params={"id": "9223372036854775807"})
    ).json()
    assert result["code"] == code, result


@pytest.mark.asyncio(loop_scope="module")
async def test_normal_and_deleted_config_and_log_details(admin_client, infra_database):
    created = (
        await admin_client.post(
            "/admin-api/infra/config/type/create",
            json={"name": "Detail", "code": uuid4().hex, "module": "infra", "status": 1},
        )
    ).json()
    assert created["code"] == 0, created
    identifier = created["data"]
    assert (
        await admin_client.get("/admin-api/infra/config/type/get", params={"id": identifier})
    ).json()["data"]["name"] == "Detail"
    assert (
        await admin_client.delete("/admin-api/infra/config/type/delete", params={"id": identifier})
    ).json()["code"] == 0
    assert (
        await admin_client.get("/admin-api/infra/config/type/get", params={"id": identifier})
    ).json()["code"] == 1001010004
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "INSERT INTO infra_job_log (id,job_id,handler_name,execute_index,status,request_id,state,creator,updater,create_time,update_time,begin_time,deleted) VALUES (991001,991002,'fixture',1,1,'fixture','succeeded','1','1',NOW(),NOW(),NOW(),0)"
        )
    result = (
        await admin_client.get("/admin-api/infra/job/log/get", params={"id": "991001"})
    ).json()
    assert result["code"] == 0 and result["data"]["jobId"] == "991002", result
    with infra_database[2].cursor() as cursor:
        cursor.execute("UPDATE infra_job_log SET deleted=1 WHERE id=991001")
    assert (await admin_client.get("/admin-api/infra/job/log/get", params={"id": "991001"})).json()[
        "code"
    ] == 404
