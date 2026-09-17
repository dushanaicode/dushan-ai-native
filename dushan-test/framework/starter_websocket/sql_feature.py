import ast
import importlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine
from starter_tenant.conftest import SOURCE as TENANT_SOURCE

from fixtures.config_factory import ConfigFactory
from starter_websocket.provider_source import SOURCE


@asynccontextmanager
async def sql_feature(target, tmp_path, module_package):
    namespace = "s" + uuid4().hex[:10]
    package = "ws_tenants_" + namespace
    source = TENANT_SOURCE.format(
        suffix=namespace,
        public="@public_data(tenant_column=None)",
        protected='@data_permission(permission_type="both", user_id_column="membership_id", dept_id_column="dept_id")',
    )
    lines = source.splitlines()
    removed = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name in {"Tokens", "Permissions", "Workloads"}:
            start = min(node.lineno, *(item.lineno for item in node.decorator_list))
            removed.update(range(start - 1, node.end_lineno))
    module_package(
        package,
        scan_roots=(".",),
        files={
            "components.py": "\n".join(
                line for index, line in enumerate(lines) if index not in removed
            )
        },
    )
    module = importlib.import_module(package + ".components")
    uri = target["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'websocket.sqlite').as_posix()}"
    database = {
        **ConfigFactory.values()["config"]["models"]["database"],
        "enabled": True,
        "health_check_enabled": False,
        "sources": [dict(name="primary", url=uri, role="primary", weight=100, pool=None, tls=None)],
    }
    engine = create_async_engine(uri)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.create_all)
            now = datetime.now(UTC).replace(tzinfo=None)
            audit = dict(create_time=now, update_time=now)
            await connection.execute(
                insert(module.Directory.__table__),
                [dict(id=index, tenant_key=str(index), enabled=True, **audit) for index in (1, 2)],
            )
            await connection.execute(
                insert(module.Member.__table__),
                [
                    dict(
                        id=index,
                        tenant_key=tenant,
                        member_key=member,
                        account="account-" + member,
                        department="d1",
                        enabled=True,
                        **audit,
                    )
                    for index, tenant, member in ((1, "1", "m1"), (2, "1", "m2"), (3, "2", "m1"))
                ],
            )
            await connection.execute(
                insert(module.Record.__table__),
                [
                    dict(
                        id=index,
                        tenant_id=tenant,
                        membership_id=member,
                        dept_id="d1",
                        name=name,
                        value=index,
                        **audit,
                    )
                    for index, tenant, member, name in (
                        (1, "1", "m1", "first-member"),
                        (2, "1", "m2", "second-member"),
                        (3, "2", "m1", "other-tenant"),
                    )
                ],
            )
        websocket_source = SOURCE.replace("SecurityRealm.PLATFORM", "SecurityRealm.TENANT")
        websocket_source += f"""
from {package}.components import Record
from sqlalchemy import select
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_websocket.spi.socket_projection import SocketProjection

class RecordsPayload(BaseModel):
    ids: list[int]
    names: list[str]=[]

@service
class RecordsProjection(SocketProjection):
    def __init__(self,database: SessionProvider): self.database=database
    async def project(self,payload,context):
        async with self.database.read_session() as session:
            names=list((await session.scalars(select(Record.__table__.c.name).where(Record.id.in_(payload.ids),Record.value>0))).all())
        return RecordsPayload(ids=payload.ids,names=names)

@socket_event(EventDefinition(audience="test",type="records",payload=RecordsPayload,policy=read,projector=RecordsProjection))
class RecordsEvent:
    pass

@socket_handler(HandlerDefinition(audience="test",type="records",payload=RecordsPayload,policy=read))
class RecordsHandler(SocketHandler):
    async def handle(self,payload,context): await context.reply("records",payload)

@controller("/api/ws-sql",policy=send)
class SqlController:
    def __init__(self,database: SessionProvider,service: WebSocketService): self.database,self.service=database,service
    @route("/pool")
    async def pool(self): return self.database.get_metrics()
    @route("/send-direct",methods=("POST",))
    async def send_direct(self,command: SendInput):
        result=await self.service.send(command.target,command.message)
        return {{"accepted":result.accepted}}
"""
        yield SimpleNamespace(
            namespace=namespace,
            package=package,
            source=websocket_source,
            module=module,
            engine=engine,
            models={"database": database, "data_permission": {"enabled": True}},
        )
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.drop_all)
        await engine.dispose()
