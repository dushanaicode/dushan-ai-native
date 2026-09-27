import ast
import asyncio
import io
import json
import os
import socket
import zipfile
from pathlib import Path

import pytest
import uvicorn


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.skipif(
    os.environ.get("DUSHAN_CODEGEN_BROWSER") not in {"1", "replay"},
    reason="手动浏览器联调，仅使用本轮独立数据库",
)
async def test_codegen_browser_workflow(infra_app, infra_database, admin_client):
    work = Path(os.environ["DUSHAN_CODEGEN_WORKDIR"]).resolve()
    assert work.is_relative_to((Path.cwd() / "Temp").resolve())
    work.mkdir(parents=True, exist_ok=True)
    resources, database, connection = infra_database
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE qa_record (
                id BIGINT NOT NULL PRIMARY KEY COMMENT '编号',
                name VARCHAR(50) NOT NULL COMMENT '名称',
                status TINYINT NOT NULL DEFAULT 1 COMMENT '状态',
                amount DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '金额',
                remark VARCHAR(255) NULL COMMENT '备注',
                tenant_id VARCHAR(32) NOT NULL DEFAULT '1',
                creator VARCHAR(64) NOT NULL DEFAULT '',
                create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updater VARCHAR(64) NOT NULL DEFAULT '',
                update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted TINYINT NOT NULL DEFAULT 0
            ) COMMENT='代码生成测试记录'
        """)
    source = (
        await admin_client.post(
            "/admin-api/infra/data-source/create",
            json={
                "name": "代码生成独立测试源",
                "url": f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{database}?charset=utf8mb4",
                "status": 1,
                "dbType": "mysql",
                "sourceType": 1,
                "isDefault": False,
            },
        )
    ).json()
    assert source["code"] == 0, source
    if os.environ["DUSHAN_CODEGEN_BROWSER"] == "replay":
        imported = (
            await admin_client.post(
                "/admin-api/infra/codegen/create-list",
                json={"dataSourceConfigId": source["data"], "tableNames": ["qa_record"]},
            )
        ).json()
        assert imported["code"] == 0, imported
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            infra_app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            access_log=False,
            log_level="warning",
            log_config=None,
        )
    )
    task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(15):
            while not server.started:
                await asyncio.sleep(0.1)
        (work / "browser-server.json").write_text(
            json.dumps({"port": port, "sourceId": source["data"], "table": "qa_record"}),
            encoding="utf-8",
        )
        if os.environ["DUSHAN_CODEGEN_BROWSER"] == "1":
            async with asyncio.timeout(1200):
                while not (work / "browser-done.json").exists():
                    await asyncio.sleep(0.5)
            browser_result = json.loads((work / "browser-done.json").read_text(encoding="utf-8"))
            assert browser_result["success"], "浏览器流程未全部通过，参见browser-result.json"

        page = (
            await admin_client.get(
                "/admin-api/infra/codegen/table/page",
                params={"tableName": "qa_record", "page": 1, "pageSize": 20},
            )
        ).json()
        assert page["code"] == 0 and page["data"]["total"] == 1, page
        table_id = page["data"]["items"][0]["id"]
        detail = (
            await admin_client.get("/admin-api/infra/codegen/detail", params={"tableId": table_id})
        ).json()
        assert detail["code"] == 0, detail
        if os.environ["DUSHAN_CODEGEN_BROWSER"] == "replay":
            from module_infra.controller.admin.codegen.vo.codegen_column_update_req_vo import (
                CodegenColumnUpdateReqVO,
            )
            from module_infra.controller.admin.codegen.vo.codegen_table_update_req_vo import (
                CodegenTableUpdateReqVO,
            )

            table_fields = {field.alias for field in CodegenTableUpdateReqVO.model_fields.values()}
            column_fields = {
                field.alias for field in CodegenColumnUpdateReqVO.model_fields.values()
            }
            payload = {
                "table": {
                    key: value
                    for key, value in detail["data"]["table"].items()
                    if key in table_fields
                },
                "columns": [
                    {key: value for key, value in column.items() if key in column_fields}
                    for column in detail["data"]["columns"]
                ],
            }
            payload["table"].update(enableExport=True, remark="API隔离回放", parentMenuId="0")
            saved = (await admin_client.put("/admin-api/infra/codegen/update", json=payload)).json()
            assert saved["code"] == 0, saved
            detail = (
                await admin_client.get(
                    "/admin-api/infra/codegen/detail", params={"tableId": table_id}
                )
            ).json()
            assert detail["data"]["table"]["remark"] == "API隔离回放", detail
            assert detail["data"]["table"]["parentMenuId"] == "0", detail
            refreshed_page = (
                await admin_client.get(
                    "/admin-api/infra/codegen/table/page", params={"page": 1, "pageSize": 20}
                )
            ).json()
            assert refreshed_page["code"] == 0, refreshed_page
        (work / "detail.json").write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        preview = (
            await admin_client.get("/admin-api/infra/codegen/preview", params={"tableId": table_id})
        ).json()
        assert preview["code"] == 0, preview
        (work / "preview.json").write_text(
            json.dumps(preview, ensure_ascii=False), encoding="utf-8"
        )
        generated = work / "generated"
        for item in preview["data"]:
            output = (generated / item["filePath"]).resolve()
            assert output.is_relative_to(generated.resolve())
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(item["code"], encoding="utf-8")
            if output.suffix == ".py":
                ast.parse(item["code"], filename=item["filePath"])
        downloaded = await admin_client.get(
            "/admin-api/infra/codegen/download", params={"tableId": table_id}
        )
        assert downloaded.status_code == 200
        (work / "codegen-record.zip").write_bytes(downloaded.content)
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
            assert set(archive.namelist()) == {item["filePath"] for item in preview["data"]}
            for item in preview["data"]:
                assert archive.read(item["filePath"]).decode() == item["code"]
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE qa_record ADD extra_note VARCHAR(20) NULL COMMENT '扩展备注'"
            )
        synced = (
            await admin_client.put(
                "/admin-api/infra/codegen/sync-from-db", params={"tableId": table_id}
            )
        ).json()
        assert synced["code"] == 0, synced
        refreshed = (
            await admin_client.get("/admin-api/infra/codegen/detail", params={"tableId": table_id})
        ).json()
        assert "extra_note" in {column["columnName"] for column in refreshed["data"]["columns"]}
        deleted = (
            await admin_client.delete("/admin-api/infra/codegen/delete", params={"id": table_id})
        ).json()
        assert deleted["code"] == 0, deleted
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM qa_record")
            assert cursor.fetchone()[0] == 0
    finally:
        server.should_exit = True
        await task
