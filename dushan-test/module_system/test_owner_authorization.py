from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def created(client, path, data):
    result = (await client.post("/admin-api/system/" + path, json=data)).json()
    assert result["code"] == 0, result
    return result["data"]


async def signed_in(app, tenant, username, password):
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    result = (
        await client.post(
            "/admin-api/system/auth/login",
            json={"username": username, "password": password},
            headers={"X-Tenant-Id": tenant},
        )
    ).json()
    assert result["code"] == 0, result
    client.headers["Authorization"] = "Bearer " + result["data"]["accessToken"]
    return client


async def test_seed_package_is_explicit_and_owner_cannot_be_disabled(admin_client, system_database):
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT JSON_LENGTH(menu_ids) FROM system_tenant_package WHERE id=10100000090001"
        )
        assert cursor.fetchone()[0] > 100
    response = (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()
    assert "super_admin" in response["data"]["roles"]
    assert "system:tenant:package:create" in response["data"]["permissions"]
    assert (
        await admin_client.put(
            "/admin-api/system/user/update-status", json={"id": "10100000010001", "status": 0}
        )
    ).json()["code"] != 0
    assert (
        await admin_client.delete("/admin-api/system/user/delete", params={"id": "10100000010001"})
    ).json()["code"] != 0


async def test_legacy_super_role_binding_does_not_make_another_owner(
    admin_client, system_app, system_database
):
    username = "nonowner" + uuid4().hex[:8]
    user_id = await created(
        admin_client,
        "user/create",
        {"username": username, "nickname": "NotOwner", "password": "NotOwner123!"},
    )
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM system_role WHERE code='super_admin' AND tenant_id='1' AND deleted=0"
        )
        root_role = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO system_user_role (id,user_id,role_id,tenant_id,creator,updater,create_time,update_time,deleted) VALUES (%s,%s,%s,'1','test','test',NOW(),NOW(),0)",
            (900000000000000111, user_id, root_role),
        )
    client = await signed_in(system_app, "1", username, "NotOwner123!")
    try:
        info = (await client.get("/admin-api/system/auth/get-permission-info")).json()
        assert info["code"] == 0, info
        assert "super_admin" not in info["data"]["roles"]
        assert "*:*:*" not in info["data"]["permissions"]
        denied = (
            await client.get(
                "/admin-api/system/tenant/package/page", params={"page": 1, "pageSize": 20}
            )
        ).json()
        assert denied["code"] != 0
    finally:
        await client.aclose()


async def test_tenant_admin_is_limited_by_package_even_with_extra_role_rows(
    admin_client, system_app, system_database
):
    connection = system_database[2]
    with connection.cursor() as cursor:
        cursor.execute("SELECT id,permission,parent_id FROM system_menu WHERE deleted=0")
        rows = cursor.fetchall()
    menu_by_id = {row[0]: row for row in rows}
    user_query = next(row[0] for row in rows if row[1] == "system:user:query")
    post_query = next(row[0] for row in rows if row[1] == "system:dept:post:query")
    selected = {user_query}
    parent = menu_by_id[user_query][2]
    while parent:
        selected.add(parent)
        parent = menu_by_id[parent][2]
    suffix = uuid4().hex[:8]
    package = await created(
        admin_client,
        "tenant/package/create",
        {"name": "limited" + suffix, "status": 1, "menuIds": [str(value) for value in selected]},
    )
    tenant = await created(
        admin_client,
        "tenant/create",
        {
            "name": "limited" + suffix,
            "contactName": "Tenant Manager",
            "status": 1,
            "websites": [],
            "packageId": package,
            "expireTime": "2035-01-01T00:00:00",
            "accountCount": 20,
            "username": "admin",
            "password": "TenantTest123!",
        },
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM system_role WHERE tenant_id=%s AND code='tenant_admin' AND deleted=0",
            (tenant,),
        )
        role = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO system_role_menu (id,role_id,menu_id,tenant_id,creator,updater,create_time,update_time,deleted) VALUES (%s,%s,%s,%s,'test','test',NOW(),NOW(),0)",
            (900000000000000112, role, post_query, tenant),
        )
    client = await signed_in(system_app, tenant, "admin", "TenantTest123!")
    try:
        info = (await client.get("/admin-api/system/auth/get-permission-info")).json()
        assert info["code"] == 0, info
        assert (
            "tenant_admin" in info["data"]["roles"] and "super_admin" not in info["data"]["roles"]
        )
        assert "system:user:query" in info["data"]["permissions"]
        assert "system:dept:post:query" not in info["data"]["permissions"]
        assert (
            await client.get("/admin-api/system/user/page", params={"page": 1, "pageSize": 20})
        ).json()["code"] == 0
        assert (
            await client.get("/admin-api/system/dept/post/page", params={"page": 1, "pageSize": 20})
        ).json()["code"] != 0
        assert (
            await client.get(
                "/admin-api/system/tenant/package/page", params={"page": 1, "pageSize": 20}
            )
        ).json()["code"] != 0
        disabled = (
            await admin_client.put(
                "/admin-api/system/tenant/package/update",
                json={
                    "id": package,
                    "name": "limited" + suffix,
                    "status": 0,
                    "menuIds": [str(value) for value in selected],
                },
            )
        ).json()
        assert disabled["code"] == 0, disabled
        assert (await client.get("/admin-api/system/user/page")).json()["code"] != 0
        reduced = (
            await admin_client.put(
                "/admin-api/system/tenant/package/update",
                json={
                    "id": package,
                    "name": "limited" + suffix,
                    "status": 1,
                    "menuIds": [str(value) for value in selected if value != user_query],
                },
            )
        ).json()
        assert reduced["code"] == 0, reduced
        updated_info = (await client.get("/admin-api/system/auth/get-permission-info")).json()
        assert updated_info["code"] == 0, updated_info
        assert "system:user:query" not in updated_info["data"]["permissions"]
    finally:
        await client.aclose()
