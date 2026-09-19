"""测试身份提供者：真实 SQL 查询验证框架契约，不代表 System 登录已经迁入。"""

import asyncio
import json
import os

from sqlalchemy import JSON, Boolean, Column, MetaData, String, Table, insert, select, update
from sqlalchemy.orm import mapped_column

from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_security.bizlog.log_record_provider import LogRecordProvider
from framework.starter_security.bizlog.log_record_reservation import LogRecordReservation
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.token_provider import TokenProvider

metadata = MetaData()
sessions = Table(
    "security_test_sessions",
    metadata,
    Column("digest", String(64), primary_key=True),
    Column("data", JSON, nullable=False),
)
permissions = Table(
    "security_test_permissions",
    metadata,
    Column("binding", String(64), primary_key=True),
    Column("revision", String(64), primary_key=True),
    Column("data", JSON, nullable=False),
)
audits = Table(
    "security_test_audits",
    metadata,
    Column("event_id", String(32), primary_key=True),
    Column("done", Boolean, nullable=False),
    Column("outcome", String(32)),
    Column("data", JSON, nullable=False),
)


class AuditItem(BaseDO):
    __tablename__ = "security_test_items"
    metadata = metadata
    value = mapped_column(String(64))


class SqlTokenProvider(TokenProvider):
    def __init__(self, database: SessionProvider):
        self.database = database
        self.reads = 0

    async def resolve(self, token_digest, *, application_id, domain):
        self.reads += 1
        async with self.database.read_session(force_primary=True) as db:
            row = (
                await db.execute(select(sessions.c.data).where(sessions.c.digest == token_digest))
            ).scalar_one_or_none()
        if row is None:
            return None
        return LoginSession.model_validate_json(json.dumps(row))

    async def revoke(self, session):
        async with self.database.transaction() as db:
            rows = (await db.execute(select(sessions))).all()
            for row in rows:
                value = row.data
                if (value["application_id"], value["domain"], value["family_id"]) == (
                    session.application_id,
                    session.domain,
                    session.family_id,
                ):
                    await db.execute(
                        update(sessions)
                        .where(sessions.c.digest == row.digest)
                        .values(data={**value, "revoked": True})
                    )


class SqlPermissionProvider(PermissionProvider):
    def __init__(self, database: SessionProvider):
        self.database = database
        self.reads = 0
        self.delay = float(os.environ.get("DUSHAN_SECURITY_PERMISSION_DELAY", "0"))

    async def snapshot(self, session, *, binding):
        self.reads += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        async with self.database.read_session(force_primary=True) as db:
            data = (
                await db.execute(
                    select(permissions.c.data).where(
                        permissions.c.binding == binding,
                        permissions.c.revision == session.authorization_revision,
                    )
                )
            ).scalar_one_or_none()
        if data is None:
            raise SecurityException(SecurityErrorCodes.UNAVAILABLE)
        return PermissionSnapshot.model_validate_json(json.dumps(data))


class SqlLogRecordProvider(LogRecordProvider):
    def __init__(self, database: SessionProvider):
        self.database = database
        self.events = []
        self.renewals = 0

    async def reserve(self, operation):
        async with self.database.transaction(propagation="requires_new") as db:
            await db.execute(
                insert(audits).values(
                    event_id=operation.event_id,
                    done=False,
                    data={
                        "principal_id": operation.identity.principal_id,
                        "tenant_id": operation.identity.tenant_id,
                    },
                )
            )
        return LogRecordReservation(operation.event_id, True, operation.event_id)

    async def finalize(self, reservation, entry):
        self.events.append(entry)
        async with self.database.transaction(propagation="requires_new") as db:
            await db.execute(
                update(audits)
                .where(audits.c.event_id == reservation.event_id)
                .values(
                    done=True,
                    outcome=entry.result,
                    data={"action": entry.action, "biz_no": entry.biz_no},
                )
            )

    async def renew(self, reservation):
        self.renewals += 1

    async def cancel(self, reservation):
        async with self.database.transaction(propagation="requires_new") as db:
            await db.execute(
                update(audits)
                .where(audits.c.event_id == reservation.event_id)
                .values(done=True, outcome="cancelled")
            )
