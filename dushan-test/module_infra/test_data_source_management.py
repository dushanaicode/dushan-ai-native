import pytest
from sqlalchemy import func, select

from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_data_source_crud_probe_and_named_routing(admin_client, infra_database, infra_app):
    resources, schema, connection = infra_database
    reporting = schema + "_reporting"
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE `{reporting}` CHARACTER SET utf8mb4")
    payload = {
        "name": "Reporting fixture",
        "url": f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{reporting}?charset=utf8mb4",
        "status": 1,
        "dbType": "mysql",
        "sourceType": 1,
        "isDefault": False,
    }
    identifier = None
    try:
        created = (
            await admin_client.post("/admin-api/infra/data-source/create", json=payload)
        ).json()
        assert created["code"] == 0, created
        identifier = created["data"]
        found = (
            await admin_client.get("/admin-api/infra/data-source/get", params={"id": identifier})
        ).json()["data"]
        assert "url" not in found
        tested = (
            await admin_client.post("/admin-api/infra/data-source/test", params={"id": identifier})
        ).json()
        assert tested["code"] == 0 and tested["data"]["success"] is True, tested
        database = infra_app.state.database
        with infra_app.state.application_context.execution(), database.scope():
            async with database.read_session(source=f"infra_{identifier}") as session:
                assert await session.scalar(select(func.database())) == reporting
            async with database.read_session(force_primary=True) as session:
                assert await session.scalar(select(func.database())) == schema
        changed = (
            await admin_client.put(
                "/admin-api/infra/data-source/update",
                json={
                    **{k: v for k, v in payload.items() if k != "url"},
                    "id": identifier,
                    "name": "Renamed fixture",
                },
            )
        ).json()
        assert changed["code"] == 0, changed
        assert (
            await admin_client.post("/admin-api/infra/data-source/test", params={"id": identifier})
        ).json()["data"]["success"] is True
        for status in (0, 1):
            result = (
                await admin_client.put(
                    "/admin-api/infra/data-source/update-status",
                    json={"id": identifier, "status": status},
                )
            ).json()
            assert result["code"] == 0, result
            assert (f"infra_{identifier}" in database.get_metrics()["pools"]) is bool(status)
    finally:
        if identifier is not None:
            deleted = (
                await admin_client.delete(
                    "/admin-api/infra/data-source/delete", params={"id": identifier}
                )
            ).json()
            assert deleted["code"] == 0, deleted
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE `{reporting}`")


async def test_unavailable_driver_is_a_connection_error_without_credentials(admin_client):
    result = (
        await admin_client.post(
            "/admin-api/infra/data-source/create",
            json={
                "name": "Unavailable driver fixture",
                "url": "mysql+missing_fixture_driver://fixture:private-fixture-password@127.0.0.1:1/demo",
                "status": 1,
                "dbType": "mysql",
                "sourceType": 1,
            },
        )
    ).json()
    assert result["code"] == ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED.code, result
    assert "private-fixture-password" not in str(result)


@pytest.mark.parametrize(
    "field,value", [("poolSize", 0), ("maxOverflow", -1), ("poolTimeout", 0), ("poolRecycle", -2)]
)
async def test_invalid_pool_configuration_rejected_before_connection(admin_client, field, value):
    result = (
        await admin_client.post(
            "/admin-api/infra/data-source/create",
            json={
                "name": "Invalid pool fixture",
                "url": "mysql+aiomysql://fixture@127.0.0.1:1/demo",
                "status": 1,
                "dbType": "mysql",
                "sourceType": 1,
                field: value,
            },
        )
    ).json()
    assert result["code"] == 422, result
