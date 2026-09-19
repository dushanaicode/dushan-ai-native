from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from framework.starter_security.definitions.constants.security_error_codes import (
    SecurityErrorCodes,
)
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.mq.message.mail.mail_send_message import MailSendMessage

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize(
    "path",
    [
        "config/page",
        "config/type/page",
        "file/config/page",
        "file/page",
        "data-source/page",
        "job/page",
        "job/log/page",
        "mq/page",
        "mq/log/page",
        "logger/api-access-log/page",
        "logger/api-error-log/page",
        "online/list",
        "server/list",
        "cache/get-monitor-info",
        "websocket/status",
        "codegen/table/page",
    ],
)
async def test_read_endpoints(admin_client, path):
    response = await admin_client.get("/admin-api/infra/" + path)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 0, response.text


async def test_announcement_publish_with_realtime_enabled(admin_client, infra_database):
    title = "Realtime" + uuid4().hex
    created = (
        await admin_client.post(
            "/admin-api/system/announcement/create",
            json={
                "title": title,
                "content": "Realtime announcement",
                "status": 0,
                "category": 1,
                "publisher": "test",
            },
        )
    ).json()
    assert created["code"] == 0, created
    published = (
        await admin_client.post(
            "/admin-api/system/announcement/publish", params={"id": created["data"]}
        )
    ).json()
    assert published["code"] == 0, published
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM system_notification_message WHERE notice_title=%s", (title,)
        )
        assert cursor.fetchone()[0] > 0


async def test_configuration_crud(admin_client):
    suffix = uuid4().hex[:8]
    kind = (
        await admin_client.post(
            "/admin-api/infra/config/type/create",
            json={"name": "Test" + suffix, "code": "test" + suffix, "module": "infra", "status": 1},
        )
    ).json()
    assert kind["code"] == 0, kind
    created = (
        await admin_client.post(
            "/admin-api/infra/config/create",
            json={
                "typeId": kind["data"],
                "name": "Value",
                "key": "test." + suffix,
                "value": "7",
                "visible": True,
                "sort": 1,
            },
        )
    ).json()
    assert created["code"] == 0, created
    value = (
        await admin_client.get(
            "/admin-api/infra/config/get-value-by-key", params={"key": "test." + suffix}
        )
    ).json()
    assert value["data"] == "7", value
    assert (
        await admin_client.delete("/admin-api/infra/config/delete", params={"id": created["data"]})
    ).json()["code"] == 0
    assert (
        await admin_client.delete(
            "/admin-api/infra/config/type/delete", params={"id": kind["data"]}
        )
    ).json()["code"] == 0


async def test_database_file_upload_download_and_delete(admin_client, infra_app):
    from urllib.parse import urlsplit

    content = b"x" * 200000
    response = (
        await admin_client.post(
            "/admin-api/infra/file/upload",
            files={"file": ("test.txt", content, "text/plain")},
            data={"directory": "integration"},
        )
    ).json()
    assert response["code"] == 0, response
    path = urlsplit(response["data"]).path
    async with AsyncClient(
        transport=ASGITransport(app=infra_app), base_url="http://testserver"
    ) as public:
        download = await public.get(path)
        assert download.status_code == 200 and download.content == content, download.text[:200]
        assert "attachment" in download.headers["content-disposition"]
        assert (
            await public.get(path, headers={"If-None-Match": download.headers["etag"]})
        ).status_code == 304
    listed = (await admin_client.get("/admin-api/infra/file/page")).json()
    assert listed["code"] == 0, listed
    row = next(item for item in listed["data"]["items"] if item["url"] == response["data"])
    assert isinstance(row["id"], str) and isinstance(row["configId"], str)
    assert (
        await admin_client.delete("/admin-api/infra/file/delete", params={"id": row["id"]})
    ).json()["code"] == 0


async def test_batch_config_type_delete_uses_repeated_ids(admin_client, infra_database):
    ids = []
    for _ in range(3):
        suffix = uuid4().hex[:8]
        created = (
            await admin_client.post(
                "/admin-api/infra/config/type/create",
                json={
                    "name": "Batch" + suffix,
                    "code": "batch" + suffix,
                    "module": "infra",
                    "status": 1,
                },
            )
        ).json()
        assert created["code"] == 0, created
        ids.append(created["data"])
    for params in ({}, {"ids": ""}, {"ids": ",".join(ids)}, [("ids", ids[0]), ("ids", "invalid")]):
        rejected = (
            await admin_client.delete("/admin-api/infra/config/type/delete-list", params=params)
        ).json()
        assert rejected["code"] == 422, rejected
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT id FROM infra_config_type WHERE id IN (%s,%s,%s) AND deleted=0", ids)
        assert {str(row[0]) for row in cursor.fetchall()} == set(ids)
    child = (
        await admin_client.post(
            "/admin-api/infra/config/create",
            json={
                "typeId": ids[1],
                "name": "Batch child",
                "key": "batch." + uuid4().hex,
                "value": "kept",
                "visible": True,
                "sort": 1,
            },
        )
    ).json()
    assert child["code"] == 0, child
    rejected = (
        await admin_client.delete(
            "/admin-api/infra/config/type/delete-list", params=[("ids", value) for value in ids[:2]]
        )
    ).json()
    assert rejected["code"] == ErrorCodeConstants.CONFIG_TYPE_HAS_CHILDREN.code, rejected
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT id FROM infra_config_type WHERE id IN (%s,%s,%s) AND deleted=0", ids)
        assert {str(row[0]) for row in cursor.fetchall()} == set(ids)
    retained = (
        await admin_client.get("/admin-api/infra/config/get", params={"id": child["data"]})
    ).json()
    assert retained["code"] == 0 and retained["data"]["value"] == "kept", retained
    assert (
        await admin_client.delete("/admin-api/infra/config/delete", params={"id": child["data"]})
    ).json()["code"] == 0
    deleted = (
        await admin_client.delete(
            "/admin-api/infra/config/type/delete-list", params=[("ids", value) for value in ids[:2]]
        )
    ).json()
    assert deleted["code"] == 0 and deleted["data"] == 2, deleted
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT id FROM infra_config_type WHERE id IN (%s,%s,%s) AND deleted=0", ids)
        assert [str(row[0]) for row in cursor.fetchall()] == ids[2:]


async def test_local_file_configuration_and_paths(admin_client, tmp_path):
    payload = {
        "name": "Local" + uuid4().hex[:8],
        "storage": 10,
        "config": {"basePath": str(tmp_path / "storage"), "domain": "http://testserver"},
    }
    response = (await admin_client.post("/admin-api/infra/file/config/create", json=payload)).json()
    assert response["code"] == 0, response
    identifier = response["data"]
    response = (
        await admin_client.get("/admin-api/infra/file/config/get", params={"id": identifier})
    ).json()
    assert response["code"] == 0, response
    assert response["data"]["config"]["basePath"] == payload["config"]["basePath"]
    assert (
        await admin_client.post(
            "/admin-api/infra/file/create-directory",
            json={"configId": identifier, "directoryPath": "docs"},
        )
    ).json()["code"] == 0
    rejected = (
        await admin_client.post(
            "/admin-api/infra/file/create-directory",
            json={"configId": identifier, "directoryPath": "../outside"},
        )
    ).json()
    assert rejected["code"] == 422, rejected
    assert not (tmp_path / "outside").exists()


async def test_data_source_and_generated_code(admin_client, infra_database):
    import ast
    import io
    import zipfile

    resources, name, _ = infra_database
    payload = {
        "name": "Source" + uuid4().hex[:8],
        "url": f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{name}?charset=utf8mb4",
        "status": 1,
        "dbType": "mysql",
        "sourceType": 1,
        "isDefault": False,
    }
    created = (await admin_client.post("/admin-api/infra/data-source/create", json=payload)).json()
    assert created["code"] == 0, created
    identifier = created["data"]
    found = (
        await admin_client.get("/admin-api/infra/data-source/get", params={"id": identifier})
    ).json()
    assert found["code"] == 0, found
    assert "url" not in found["data"]
    imported = (
        await admin_client.post(
            "/admin-api/infra/codegen/create-list",
            json={
                "dataSourceConfigId": identifier,
                "tableNames": ["system_post", "system_dict_type", "system_dict_data"],
            },
        )
    ).json()
    assert imported["code"] == 0, imported
    table_id = imported["data"][0]
    preview = (
        await admin_client.get("/admin-api/infra/codegen/preview", params={"tableId": table_id})
    ).json()
    assert preview["code"] == 0, preview
    paths = []
    for item in preview["data"]:
        paths.append(item["filePath"])
        assert "dal/mysql" not in item["filePath"]
        if item["filePath"].endswith(".py"):
            ast.parse(item["code"])
            assert "security.core.dependencies" not in item["code"]
    assert any("/dal/mapper/" in path for path in paths)
    generated_do = next(
        item["code"] for item in preview["data"] if item["filePath"].endswith("_do.py")
    )
    assert "Computed(" in generated_do and "TenantBaseDO" in generated_do
    generated_api = next(
        item["code"]
        for item in preview["data"]
        if "/api/" in item["filePath"] and item["filePath"].endswith(".ts")
    )
    assert "id?: string" in generated_api
    menu = next(item["code"] for item in preview["data"] if item["filePath"].endswith("_menu.sql"))
    with infra_database[2].cursor() as cursor:
        cursor.execute(menu)
        while cursor.nextset():
            pass
    response = await admin_client.get(
        "/admin-api/infra/codegen/download", params={"tableId": table_id}
    )
    assert response.status_code == 200, response.text[:100]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == set(paths)
    ids = imported["data"]
    assert len(ids) == 3
    for params in ({}, {"ids": ",".join(ids)}, [("ids", ids[0]), ("ids", "invalid")]):
        rejected = (
            await admin_client.delete("/admin-api/infra/codegen/delete-list", params=params)
        ).json()
        assert rejected["code"] == 422, rejected
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM infra_codegen_table WHERE id IN (%s,%s,%s) AND deleted=0", ids
        )
        assert {str(row[0]) for row in cursor.fetchall()} == set(ids)
    deleted = (
        await admin_client.delete(
            "/admin-api/infra/codegen/delete-list", params=[("ids", value) for value in ids[:2]]
        )
    ).json()
    assert deleted["code"] == 0 and deleted["data"] is True, deleted
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM infra_codegen_table WHERE id IN (%s,%s,%s) AND deleted=0", ids
        )
        assert [str(row[0]) for row in cursor.fetchall()] == ids[2:]


async def test_job_trigger_is_durable_and_records_result(admin_client, infra_database):
    import asyncio

    _, _, connection = infra_database
    job_id = "10300000050005"
    response = (
        await admin_client.put("/admin-api/infra/job/trigger", params={"id": job_id})
    ).json()
    assert response["code"] == 0, response
    async with asyncio.timeout(15):
        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state FROM infra_job_request WHERE job_id=%s ORDER BY id DESC LIMIT 1",
                    (job_id,),
                )
                row = cursor.fetchone()
            if row and row[0] not in {"pending", "claimed"}:
                break
            await asyncio.sleep(0.05)
    assert row[0] == "succeeded", row
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT state FROM infra_job_log WHERE job_id=%s ORDER BY id DESC LIMIT 1", (job_id,)
        )
        assert cursor.fetchone()[0] == "succeeded"


async def test_database_backup_uses_owned_instance(infra_app):
    from pathlib import Path

    from module_infra.job.data_source.database_backup_job import DatabaseBackupJob
    from module_infra.job.data_source.database_backup_parameters import DatabaseBackupParameters
    from module_system.api.auth.workload_api import WorkloadApi

    application = infra_app.state.application_context
    with application.execution(), infra_app.state.database.scope():
        async with application.container.get(WorkloadApi).scope("infra.database.backup", "1"):
            file = Path(
                await application.container.get(DatabaseBackupJob).execute(
                    DatabaseBackupParameters(), None
                )
            )
    assert file.resolve().is_relative_to(
        Path(infra_app.state.bootstrap.base_dir).resolve() / "Temp"
    )
    data = file.read_text(encoding="utf-8")
    assert "CREATE TABLE `infra_job_request`" in data
    assert "CREATE TABLE `system_users`" in data


async def test_real_message_delivery_and_safe_observation(admin_client, infra_app, infra_database):
    import asyncio

    from framework.starter_security.core.security_service import SecurityService
    from framework.starter_security.definitions.enums.security_realm import SecurityRealm
    from framework.starter_web.routing.route_policy import RoutePolicy
    from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
    from module_system.dal.dataobject.mail.mail_log_do import MailLogDO
    from module_system.dal.mapper.mail.mail_account_mapper import MailAccountMapper
    from module_system.dal.mapper.mail.mail_log_mapper import MailLogMapper
    from module_system.mq.producer.mail.mail_producer_protocol import MailProducerProtocol

    application = infra_app.state.application_context
    message_id = uuid4().hex
    with application.execution(), infra_app.state.database.scope():
        security = application.container.get(SecurityService)
        async with security.authorized(
            admin_client.headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            account = await application.container.get(MailAccountMapper).insert(
                MailAccountDO(
                    mail="sender@example.com",
                    username="sender",
                    password="unused",
                    host="127.0.0.1",
                    port=1,
                    ssl_enable=False,
                    starttls_enable=False,
                )
            )
            record = await application.container.get(MailLogMapper).insert(
                MailLogDO(
                    user_type=2,
                    to_mail="receiver@example.com",
                    account_id=account.id,
                    from_mail="sender@example.com",
                    template_id=1,
                    template_code="test",
                    template_title="Test",
                    template_content="not-for-observation",
                    template_params={},
                    send_status=10,
                )
            )
            await application.container.get(MailProducerProtocol).send_mail_message(
                MailSendMessage(
                    message_id=message_id,
                    log_id=record.id,
                    to_mails=["receiver@example.com"],
                    account_id=account.id,
                    nickname=None,
                    title="Test",
                    content="not-for-observation",
                )
            )
    _, _, connection = infra_database
    async with asyncio.timeout(15):
        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state,payload,result FROM infra_mq_log WHERE message_id=%s ORDER BY id DESC LIMIT 1",
                    (message_id,),
                )
                row = cursor.fetchone()
            if row:
                break
            await asyncio.sleep(0.05)
    assert row[0] == "succeeded", row
    assert row[1] in (None, "null") and "not-for-observation" not in str(row)


async def test_live_websocket_commands(admin_client, infra_app):
    import asyncio
    import json
    import socket

    from uvicorn import Config, Server
    from websockets.asyncio.client import connect

    ticket = (await admin_client.post("/admin-api/system/auth/websocket-ticket")).json()
    assert ticket["code"] == 0, ticket
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.setblocking(False)
    port = listener.getsockname()[1]
    server = Server(
        Config(
            infra_app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_config=None,
            access_log=False,
        )
    )
    serving = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                await asyncio.sleep(0.01)
        async with connect(
            f"ws://127.0.0.1:{port}/api/ws?audience=infra&ticket={ticket['data']}",
            origin="http://testserver",
            proxy=None,
        ) as ws:
            assert json.loads(await ws.recv())["type"] == "connect"
            for kind in ("get-user-info", "get-server-usage-data"):
                await ws.send(json.dumps({"type": kind, "payload": {}, "requestId": kind}))
                result = json.loads(await asyncio.wait_for(ws.recv(), 5))
                assert result["type"] == kind + "-response", result
                assert result["requestId"] == kind
                if kind == "get-user-info":
                    assert isinstance(result["payload"]["data"]["id"], str)
            sent = (
                await admin_client.post(
                    "/admin-api/infra/websocket/broadcast",
                    json={"message": {"type": "text", "payload": "delivered"}},
                )
            ).json()
            assert sent["code"] == 0, sent
            assert (
                json.loads(await asyncio.wait_for(ws.recv(), 5))["payload"]["payload"]
                == "delivered"
            )
    finally:
        server.should_exit = True
        await serving
        listener.close()


async def test_job_definition_crud_notifies_runtime(admin_client):
    assert (
        await admin_client.delete("/admin-api/infra/job/delete", params={"id": "10300000050007"})
    ).json()["code"] == 0
    request = {
        "name": "Backup test",
        "handlerName": "infra.database.backup",
        "handlerParam": "{}",
        "cronExpression": "0 0 1 1 *",
        "retryCount": 0,
        "retryInterval": 0,
        "monitorTimeout": 300000,
    }
    response = (await admin_client.post("/admin-api/infra/job/create", json=request)).json()
    assert response["code"] == 0, response
    identifier = response["data"]
    changed = (
        await admin_client.put(
            "/admin-api/infra/job/update", json={**request, "id": identifier, "name": "Updated"}
        )
    ).json()
    assert changed["code"] == 0, changed
    stopped = (
        await admin_client.put(
            "/admin-api/infra/job/update-status", params={"id": identifier, "status": 2}
        )
    ).json()
    assert stopped["code"] == 0, stopped
    assert (
        await admin_client.delete("/admin-api/infra/job/delete", params={"id": identifier})
    ).json()["code"] == 0


@pytest.mark.parametrize(
    "path",
    [
        "config",
        "config/type",
        "data-source",
        "job",
        "job/log",
        "mq",
        "mq/log",
        "logger/api-access-log",
        "logger/api-error-log",
    ],
)
async def test_excel_exports(admin_client, path, infra_app):
    if path == "logger/api-access-log":
        async with AsyncClient(
            transport=ASGITransport(app=infra_app), base_url="http://testserver"
        ) as anonymous:
            rejected = (await anonymous.get("/admin-api/infra/config/page")).json()
            assert rejected["code"] == SecurityErrorCodes.MISSING.code, rejected
    response = await admin_client.get("/admin-api/infra/" + path + "/export-excel")
    assert response.status_code == 200, response.text[:200]
    assert response.content.startswith(b"PK"), response.text[:300]


async def test_unauthorized_access_and_foreign_tenant_file(infra_app, infra_database, admin_client):
    _, _, connection = infra_database
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO infra_file_config(id,tenant_id,name,storage,config,master,status,creator,updater,create_time,update_time,deleted) VALUES (999999999999,'999','Foreign',1,'{\"domain\":\"http://testserver\"}',0,1,'','',UTC_TIMESTAMP(),UTC_TIMESTAMP(),0)"
        )
    async with AsyncClient(
        transport=ASGITransport(app=infra_app), base_url="http://testserver"
    ) as public:
        assert (await public.get("/admin-api/infra/file/config/page")).json()[
            "code"
        ] == SecurityErrorCodes.MISSING.code
        response = (await public.get("/admin-api/infra/file/999999999999/get/secret.txt")).json()
        assert response["code"] != 0, response
    response = (
        await admin_client.get("/admin-api/infra/file/config/get", params={"id": "999999999999"})
    ).json()
    assert response["code"] == 0 and response["data"] is None, response
