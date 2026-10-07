import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_web.public import RoutePolicy
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.mapper.notification import notice_message_mapper as notice_mapper_module
from module_system.dal.mapper.notification.notice_message_mapper import NoticeMessageMapper
from module_system.mq.producer.mail.mail_producer import MailProducer
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO
from module_system.service.mail.mail_send_service import MailSendService
from module_system.service.workload.system_workload_service import SystemWorkloadService


@asynccontextmanager
async def authorized(app, client):
    application = app.state.application_context
    with application.execution(), app.state.database.scope():
        async with application.container.get(SecurityService).authorized(
            client.headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            yield application.container


async def create(client, path, body):
    result = (await client.post(f"/admin-api/system/{path}/create", json=body)).json()
    assert result["code"] == 0, result
    return result["data"]


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def smtp_server():
    senders, messages = [], []
    active = set()

    async def receive(reader, writer):
        active.add(asyncio.current_task())
        try:
            writer.write(b"220 fixture SMTP\r\n")
            await writer.drain()
            while line := await reader.readline():
                command = line.decode().strip()
                if command.startswith("EHLO"):
                    writer.write(b"250-fixture\r\n250 AUTH PLAIN\r\n")
                elif command.startswith("AUTH"):
                    writer.write(b"235 authenticated\r\n")
                elif command.startswith("MAIL FROM:"):
                    senders.append(command)
                    writer.write(b"250 sender accepted\r\n")
                elif command == "DATA":
                    writer.write(b"354 send data\r\n")
                    await writer.drain()
                    body = []
                    while (part := await reader.readline()) != b".\r\n":
                        assert part
                        body.append(part)
                    messages.append(b"".join(body))
                    writer.write(b"250 queued as fixture-mail\r\n")
                else:
                    writer.write(b"250 accepted\r\n")
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            active.discard(asyncio.current_task())

    server = await asyncio.start_server(receive, "127.0.0.1", 0)
    try:
        yield server.sockets[0].getsockname()[1], senders, messages
    finally:
        server.close()
        await server.wait_closed()
        if active:
            await asyncio.wait_for(asyncio.gather(*active), 5)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def mail_setup(admin_client, smtp_server):
    port = smtp_server[0]
    accounts = []
    for name in ("selected-a", "template-b"):
        accounts.append(
            await create(
                admin_client,
                "mail/account",
                {
                    "mail": name + "@example.test",
                    "username": name,
                    "password": "FixtureOnly123",
                    "host": "127.0.0.1",
                    "port": port,
                    "sslEnable": False,
                    "starttlsEnable": False,
                },
            )
        )
    template = await create(
        admin_client,
        "mail/template",
        {
            "name": "Notice template",
            "code": "system-notice-mail",
            "accountId": accounts[1],
            "nickname": "Fixture",
            "title": "{title}",
            "content": "{content}",
            "status": 1,
        },
    )
    user = await create(
        admin_client,
        "user",
        {
            "username": "mail" + uuid4().hex[:10],
            "nickname": "Receiver",
            "password": "Test123!",
            "email": "receiver@example.test",
        },
    )
    return accounts, template, user


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "mode", ["selected", "missing", "deleted", "none", "disabled_template", "other_tenant_notice"]
)
async def test_notice_account_selection_and_current_boundaries(
    mode, admin_client, system_app, system_database, mail_setup, smtp_server, monkeypatch
):
    accounts, template, user = mail_setup
    assert "tenant_id" not in MailAccountDO.__table__.columns
    assert "status" not in MailAccountDO.__table__.columns
    messages = []

    async def publish(self, message):
        messages.append(message)

    monkeypatch.setattr(MailProducer, "send_mail_message", publish)
    selected = (
        None if mode == "none" else "9223372036854775807" if mode == "missing" else accounts[0]
    )
    notice = await create(
        admin_client,
        "notification",
        {
            "title": "Account selection",
            "content": "Fixture content",
            "type": 2,
            "userType": 2,
            "channels": ["MAIL"],
            "mailAccountId": selected,
            "status": 1,
            "publisher": "Fixture",
        },
    )
    connection = system_database[2]
    with connection.cursor() as cursor:
        if mode == "deleted":
            cursor.execute("UPDATE system_mail_account SET deleted=1 WHERE id=%s", (accounts[0],))
        if mode == "disabled_template":
            cursor.execute("UPDATE system_mail_template SET status=0 WHERE id=%s", (template,))
        if mode == "other_tenant_notice":
            cursor.execute(
                "UPDATE system_notification_notice SET tenant_id='outside' WHERE id=%s", (notice,)
            )
    try:
        result = (
            await admin_client.post(
                "/admin-api/system/notification/push-targets",
                json={"id": notice, "userIds": [user]},
            )
        ).json()
        if mode != "selected":
            assert result["code"] == (1002008001 if mode == "other_tenant_notice" else 503), result
            assert messages == []
            return
        assert result["code"] == 0, result
        assert len(messages) == 1
        assert messages[0].account_id == int(accounts[0])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT account_id,from_mail FROM system_mail_log WHERE id=%s",
                (messages[0].log_id,),
            )
            assert cursor.fetchone() == (int(accounts[0]), "selected-a@example.test")
        application = system_app.state.application_context
        with application.execution(), system_app.state.database.scope():
            async with application.container.get(SystemWorkloadService).scope(
                "system.mail.send", "1"
            ):
                await application.container.get(MailSendService).do_send_mail(messages[0])
        assert "selected-a@example.test" in smtp_server[1][-1]
        assert b"Fixture content" in smtp_server[2][-1]
        async with authorized(system_app, admin_client) as container:
            await container.get(MailSendService).send_multiple_mail_to_admin(
                MailBatchSendBO(
                    to_mails=["receiver@example.test"],
                    cc_mails=None,
                    bcc_mails=None,
                    user_id=int(user),
                    template_code="system-notice-mail",
                    template_params={"title": "Template", "content": "Template sends through B"},
                )
            )
        assert messages[-1].account_id == int(accounts[1])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT account_id,from_mail FROM system_mail_log WHERE id=%s",
                (messages[-1].log_id,),
            )
            assert cursor.fetchone() == (int(accounts[1]), "template-b@example.test")
    finally:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE system_mail_account SET deleted=0 WHERE id=%s", (accounts[0],))
            cursor.execute("UPDATE system_mail_template SET status=1 WHERE id=%s", (template,))


@pytest.mark.asyncio(loop_scope="module")
async def test_read_time_is_utc_naive_with_non_utc_clock(
    admin_client, system_app, system_database, monkeypatch
):
    instant = datetime(2026, 9, 26, 12, 34, 56, tzinfo=timezone.utc)

    class NonUtcClock(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instant.astimezone(timezone(timedelta(hours=-7))).replace(tzinfo=None)
            return instant.astimezone(tz)

    monkeypatch.setattr(notice_mapper_module, "datetime", NonUtcClock)
    async with authorized(system_app, admin_client) as container:
        user_id = int(container.get(SecurityService).context.require().account_id)
        base = int(uuid4().hex[:12], 16)
        previous = instant.replace(tzinfo=None) - timedelta(minutes=1)
        rows = [
            (base, user_id, 2, "1", False, False, None),
            (base + 1, user_id, 2, "1", False, False, None),
            (base + 2, user_id + 1, 2, "1", False, False, None),
            (base + 3, user_id, 1, "1", False, False, None),
            (base + 4, user_id + 2, 2, "outside", False, False, None),
            (base + 5, user_id, 2, "1", True, False, previous),
            (base + 6, user_id, 2, "1", False, True, None),
        ]
        with system_database[2].cursor() as cursor:
            for identifier, recipient, kind, tenant, read, deleted, read_time in rows:
                cursor.execute(
                    "INSERT INTO system_notification_message (id,user_id,user_type,tenant_id,notice_id,notice_title,notice_content,notice_type,sent_channels,read_status,read_time,deleted,creator,updater,create_time,update_time) VALUES (%s,%s,%s,%s,1,'Clock','Clock',2,'[]',%s,%s,%s,'fixture','fixture',%s,%s)",
                    (
                        identifier,
                        recipient,
                        kind,
                        tenant,
                        read,
                        read_time,
                        deleted,
                        previous,
                        previous,
                    ),
                )
        mapper = container.get(NoticeMessageMapper)
        assert (
            await mapper.update_list_read(
                [base, base + 2, base + 3, base + 4, base + 5, base + 6], user_id, 2
            )
            == 1
        )
        assert await mapper.update_list_read_all(user_id, 2) == 1
        instant += timedelta(hours=1)
        assert await mapper.update_list_read_all(user_id, 2) == 0
        assert await mapper.update_list_read([base], user_id, 2) == 0
        with pytest.raises(TenantException):
            await mapper.update_list_read([base + 4], user_id + 2, 2)
        with pytest.raises(TenantException):
            await mapper.update_list_read_all(user_id + 2, 2)
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id,read_status,read_time FROM system_notification_message WHERE id BETWEEN %s AND %s ORDER BY id",
            (base, base + 6),
        )
        actual = cursor.fetchall()
    expected = previous + timedelta(minutes=1)
    assert actual[:2] == ((base, 1, expected), (base + 1, 1, expected))
    assert actual[2:] == (
        (base + 2, 0, None),
        (base + 3, 0, None),
        (base + 4, 0, None),
        (base + 5, 1, previous),
        (base + 6, 0, None),
    )
