import asyncio
import json
import os
import socket
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
import yaml

from fixtures.config_factory import ConfigFactory
from fixtures.http_route_coverage import HttpRouteCoverage


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.skipif(os.environ.get("DUSHAN_FRONTEND_AUDIT") != "1", reason="完整浏览器测试宿主")
async def test_frontend_audit_host(infra_database, monkeypatch):
    from module_system.framework.mail.client.smtp_mail_client import SmtpMailClient
    from module_system.framework.sms.client.providers.aliyun_sms_client import AliyunSmsClient
    from module_system.framework.sms.enums.sms_template_audit_status_enum import (
        SmsTemplateAuditStatusEnum,
    )
    from module_system.framework.sms.model.sms_send_resp_dto import SmsSendRespDTO
    from module_system.framework.sms.model.sms_template_resp_dto import SmsTemplateRespDTO
    from server.starter_server import create_app

    work = Path(os.environ["DUSHAN_AUDIT_WORKDIR"]).resolve()
    assert work.is_relative_to((Path.cwd() / "Temp").resolve())
    work.mkdir(parents=True, exist_ok=True)
    resources, database, connection = infra_database

    def port():
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            return candidate.getsockname()[1]

    api_port, web_port, dev_port = port(), port(), port()
    origin = f"http://localhost:{web_port}"
    origins = [origin, f"http://localhost:{dev_port}"]
    messages = []

    async def smtp(reader, writer):
        writer.write(b"220 qa.local ESMTP\r\n")
        await writer.drain()
        while line := await reader.readline():
            command = line.split(b" ", 1)[0].strip().upper()
            if command in {b"EHLO", b"HELO"}:
                writer.write(b"250-qa.local\r\n250-AUTH PLAIN\r\n250 8BITMIME\r\n")
            elif command == b"AUTH":
                writer.write(b"235 Authentication successful\r\n")
            elif command == b"DATA":
                writer.write(b"354 End with dot\r\n")
                await writer.drain()
                payload = await reader.readuntil(b"\r\n.\r\n")
                messages.append({"id": str(uuid4()), "payload": payload.decode("utf-8", "replace")})
                (work / "mail-inbox.json").write_text(json.dumps(messages), encoding="utf-8")
                writer.write(b"250 queued as qa-message\r\n")
            elif command == b"QUIT":
                writer.write(b"221 Bye\r\n")
                await writer.drain()
                break
            else:
                writer.write(b"250 OK\r\n")
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    smtp_server = await asyncio.start_server(smtp, "127.0.0.1", 0)
    smtp_port = smtp_server.sockets[0].getsockname()[1]
    original_send = SmtpMailClient._send_message

    async def local_mail(account, *args):
        assert account.host == "127.0.0.1" and account.port == smtp_port, "仅允许本地SMTP测试接收器"
        return await original_send(account, *args)

    sms_messages = []

    async def local_sms(
        self, send_log_id, mobile, api_template_id, template_params, *, on_request_started
    ):
        await on_request_started()
        sms_messages.append(
            {
                "logId": str(send_log_id),
                "mobile": mobile,
                "template": api_template_id,
                "params": template_params,
            }
        )
        (work / "sms-inbox.json").write_text(json.dumps(sms_messages), encoding="utf-8")
        return SmsSendRespDTO(
            success=True,
            api_request_id="qa-request",
            serial_no="qa-sms",
            api_code="OK",
            api_msg="本地测试适配器",
        )

    async def local_template(self, api_template_id):
        return SmsTemplateRespDTO(
            id=api_template_id,
            content="测试 {code}",
            audit_status=SmsTemplateAuditStatusEnum.SUCCESS.code,
        )

    monkeypatch.setattr(SmtpMailClient, "_send_message", local_mail)
    monkeypatch.setattr(AliyunSmsClient, "send_sms", local_sms)
    monkeypatch.setattr(AliyunSmsClient, "get_sms_template", local_template)
    values = ConfigFactory.values()
    ConfigFactory.merge(
        values,
        {
            "modules": {"enabled": ["framework", "system", "infra"]},
            "server": {"reload": False},
            "log": {"enable_file_overall": False, "console_level": "WARNING"},
            "expression": {"enabled": True},
            "page": {"fetch_all_enabled": True},
            "config": {
                "reload_enabled": True,
                "models": {
                    "database": {
                        "enabled": True,
                        "health_check_enabled": False,
                        "dynamic_enabled": True,
                        "id_strategy": "snowflake",
                        "snowflake_machine_id": 927,
                        "sources": [
                            {
                                "name": "primary",
                                "url": f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{database}?charset=utf8mb4",
                                "role": "primary",
                                "weight": 100,
                                "pool": None,
                                "tls": None,
                            }
                        ],
                    },
                    "cache": {
                        "enabled": True,
                        "host": "127.0.0.1",
                        "port": resources["redis_port"],
                    },
                    "security": {
                        "enabled": True,
                        "permission_cache_enabled": True,
                        "bizlog_enabled": True,
                    },
                    "data_permission": {"enabled": True, "cache_enabled": True},
                    "protection": {"enabled": True},
                    "ip": {"enabled": True, "online_enabled": False},
                    "system": {
                        "user_register_enabled": False,
                        "workload_credential": uuid4().hex + uuid4().hex,
                        "default_password": "QAImported123!",
                        "sms_callback_token": uuid4().hex + uuid4().hex,
                        "message_signing_key": uuid4().hex + uuid4().hex,
                        "refresh_cookie_secure": False,
                        "allowed_origins": origins,
                    },
                    "job": {
                        "enabled": True,
                        "owner_enabled": True,
                        "poll_seconds": 0.1,
                        "reconciliation_seconds": 0.5,
                    },
                    "mq": {"enabled": True, "signing_secret": uuid4().hex + uuid4().hex},
                    "websocket": {
                        "enabled": True,
                        "signing_secret": uuid4().hex + uuid4().hex,
                        "allowed_origins": origins,
                    },
                    "infra_backup": {
                        "enabled": True,
                        "executable": "C:/Program Files/MySQL/MySQL Server 8.4/bin/mysqldump.exe",
                        "output_directory": str(work / "backups"),
                    },
                },
            },
        },
    )
    folder = work / "config"
    folder.mkdir(exist_ok=True)
    (folder / "application.yaml").write_text(
        yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
    )
    with connection.cursor() as cursor:
        for table in ["system_sms_channel", "system_mail_account", "system_social_client"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            assert cursor.fetchone()[0] == 0, f"测试初始化库存在外部渠道配置：{table}"
        cursor.execute("SELECT id,config FROM infra_file_config")
        for identifier, config in cursor.fetchall():
            data = json.loads(config) if isinstance(config, str) else config
            data["domain"] = origin
            cursor.execute(
                "UPDATE infra_file_config SET config=%s WHERE id=%s", (json.dumps(data), identifier)
            )
        cursor.execute(
            "CREATE TABLE qa_codegen_record (id BIGINT PRIMARY KEY, name VARCHAR(50) NOT NULL COMMENT '名称', tenant_id VARCHAR(32) NOT NULL DEFAULT '1', creator VARCHAR(64) NOT NULL DEFAULT '', create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updater VARCHAR(64) NOT NULL DEFAULT '', update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted TINYINT NOT NULL DEFAULT 0) COMMENT='浏览器测试表'"
        )
    app = create_app(base_dir=folder, app_env="dev", environ={})
    app.add_middleware(HttpRouteCoverage)
    async with app.router.lifespan_context(app):
        HttpRouteCoverage.register(app)
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=api_port,
                lifespan="off",
                access_log=False,
                log_level="warning",
                log_config=None,
            )
        )
        task = asyncio.create_task(server.serve())
        try:
            async with asyncio.timeout(20):
                while not server.started:
                    await asyncio.sleep(0.1)
            (work / "server.json").write_text(
                json.dumps(
                    {
                        "apiPort": api_port,
                        "webPort": web_port,
                        "devPort": dev_port,
                        "origin": origin,
                        "database": database,
                        "mysqlPort": resources["mysql_port"],
                        "redisPort": resources["redis_port"],
                        "smtpPort": smtp_port,
                    }
                ),
                encoding="utf-8",
            )
            async with asyncio.timeout(6 * 60 * 60):
                while not (work / "stop.json").exists():
                    await asyncio.sleep(0.5)
                    HttpRouteCoverage.save(work / "route-coverage.json")
                    mq = app.state.mq
                    job = app.state.job
                    (work / "runtime-state.json").write_text(
                        json.dumps(
                            {
                                "mq": {
                                    "phase": mq.phase,
                                    "paused": sorted(mq.paused),
                                    "errors": mq.resources()["background_error_types"],
                                    "recovering": mq.resources()["recovering_consumers"],
                                    "actors": {
                                        key: {
                                            "done": actor.done(),
                                            "cancelled": actor.cancelled(),
                                            "stack": [
                                                {
                                                    "function": frame.f_code.co_name,
                                                    "line": frame.f_lineno,
                                                }
                                                for frame in actor.get_stack()
                                            ],
                                        }
                                        for key, actor in mq.actors.items()
                                    },
                                },
                                "job": {
                                    "phase": job.phase,
                                    "owner": job.owner,
                                    "accepting": job.accepting,
                                    "failure": None
                                    if job.failure is None
                                    else type(job.failure).__name__,
                                    "counts": dict(job.counts),
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
        finally:
            server.should_exit = True
            await task
            HttpRouteCoverage.save(work / "route-coverage.json")
            smtp_server.close()
            await smtp_server.wait_closed()
