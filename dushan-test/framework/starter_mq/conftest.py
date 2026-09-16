import ast
import asyncio
import importlib
import json
import os
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from framework.starter_job.core.job_service import JobService
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.core.outbox_service import OutboxService
from framework.starter_mq.model.publish_command import PublishCommand
from framework.starter_mq.spi.outbox_provider import OutboxProvider
from server.starter_server import create_app

SOURCE = """
import asyncio
import base64
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC,datetime,timedelta
from pydantic import BaseModel,ConfigDict
from framework.starter_di.decorators.components import service
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_mq.decorators.consumer import consumer
from framework.starter_mq.decorators.message_interceptor import message_interceptor
from framework.starter_mq.handler.message_handler import MessageHandler
from framework.starter_mq.model.consumer_definition import ConsumerDefinition
from framework.starter_mq.model.retry_policy import RetryPolicy
from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.enums.exhausted_policy import ExhaustedPolicy
from framework.starter_mq.enums.tenant_policy import TenantPolicy
from framework.starter_mq.exception.message_rejected import MessageRejected
from framework.starter_mq.exception.message_result_unknown import MessageResultUnknown
from framework.starter_mq.spi.consume_record_provider import ConsumeRecordProvider
from framework.starter_mq.spi.external_message_authenticator import ExternalMessageAuthenticator
from framework.starter_mq.model.message_envelope import MessageEnvelope
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.model.workload_message import WorkloadMessage
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.routing.route_policy import RoutePolicy

tag=ContextVar("mq_test_tag",default=None)
producer_tag=ContextVar("mq_producer_tag",default=None)

@service
class Probe:
    def __init__(self):
        self.runs=[]; self.finished=[]; self.records=[]; self.instances=[]; self.executions=[]
        self.changed=asyncio.Event(); self.gate=asyncio.Event(); self.cancelled=asyncio.Event()
        self.active=0; self.peak=0; self.revoked=False; self.auth_failure=False
        self.record_failure=False; self.cleanup_failure=False; self.contexts=[]; self.times=[]; self.visible=[]

class Payload(BaseModel):
    model_config=ConfigDict(extra="forbid")
    value: int
    behavior: str="ok"
    secret: str="sensitive-mq-payload"

@service
class External(ExternalMessageAuthenticator):
    SECRET=b"separate-external-transport-key"
    async def authenticate(self,payload,*,destination):
        try:
            encoded,signature=payload.split(b".")
            body=base64.b64decode(encoded,validate=True)
            if not hmac.compare_digest(signature,hmac.new(self.SECRET,body,hashlib.sha256).hexdigest().encode()): raise ValueError()
            return MessageEnvelope.model_validate_json(body)
        except (ValueError,TypeError) as error:
            raise MQException("authentication") from error

definition=ConsumerDefinition(key="controlled",destination="events",mode=MessageMode("__MODE__"),
    message=Payload,group=__GROUP__,retry=RetryPolicy(count=__RETRIES__,delay_seconds=0.2,backoff=2,max_delay_seconds=0.8),
    exhausted=ExhaustedPolicy("__EXHAUSTED__"),tenant_policy=TenantPolicy("__TENANT__"),
    session_policy=None,workload_capabilities=frozenset(("mq:test",)),external_authenticator=__EXTERNAL__)

@consumer(definition)
class Controlled(MessageHandler):
    def __init__(self,probe: Probe,security: SecurityContext): self.probe,self.security=probe,security
    async def handle(self,message,context):
        assert tag.get()==context.message_id
        assert producer_tag.get() is None
        identity=self.security.current()
        workload=self.security.current_workload()
        assert (identity is None)!=(workload is None)
        assert (identity if identity is not None else workload).tenant_id==context.tenant_id
        if workload is not None: assert workload.capabilities==frozenset(("mq:test",))
        __SQL_QUERY__
        probe=self.probe
        probe.active+=1; probe.peak=max(probe.peak,probe.active)
        probe.instances.append(self); probe.executions.append(ApplicationContext.current_execution())
        probe.runs.append((message.value,context.attempt,context.message_id,context.tenant_id))
        probe.times.append(__import__("time").monotonic())
        probe.changed.set()
        try:
            if message.behavior in ("wait","resist"):
                try: await probe.gate.wait()
                except asyncio.CancelledError:
                    probe.cancelled.set(); probe.changed.set()
                    if message.behavior!="resist": raise
                    await probe.gate.wait()
            if message.behavior=="fail" or message.behavior=="retry" and context.attempt==0: raise ValueError(message.secret)
            if message.behavior=="reject": raise MessageRejected(message.secret)
            if message.behavior=="unknown": raise MessageResultUnknown(message.secret)
            probe.finished.append(message.value)
        finally:
            probe.active-=1; probe.changed.set()

@message_interceptor(order=1)
class Interceptor:
    def __init__(self,probe: Probe): self.probe=probe
    @asynccontextmanager
    async def enter(self,context):
        assert tag.get() is None
        token=tag.set(context.message_id)
        self.probe.contexts.append(("enter",context.message_id))
        try: yield
        finally:
            tag.reset(token)
            self.probe.contexts.append(("exit",context.message_id))
            if self.probe.cleanup_failure: raise RuntimeError("observation-only-cleanup")

@service(interface=ConsumeRecordProvider)
class Records(ConsumeRecordProvider):
    def __init__(self,probe: Probe): self.probe=probe
    async def append(self,record):
        if self.probe.record_failure: raise RuntimeError("observation unavailable")
        self.probe.records.append(record); self.probe.changed.set()

@service(interface=TokenProvider)
class Tokens(TokenProvider):
    async def resolve(self,*args,**kwargs): return None
@service(interface=PermissionProvider)
class Permissions(PermissionProvider):
    async def snapshot(self,*args,**kwargs): raise SecurityException("denied")
@service(interface=WorkloadProvider)
class Workloads(WorkloadProvider):
    def __init__(self,probe: Probe): self.probe=probe
    async def authenticate(self,source,*,application_id,domain,capability,tenant_id):
        if self.probe.revoked or (source,capability) not in (("mq-test","mq:test"),("mq.outbox","mq:dispatch")):
            raise SecurityException("denied")
        return WorkloadIdentity(application_id=application_id,domain=domain,service_id=source,
            tenant_id=tenant_id,audience=source,capabilities=frozenset((capability,)),
            expires_at=datetime.now(UTC)+timedelta(minutes=5))

@service(interface=MessageSecurityProvider)
class Proofs(MessageSecurityProvider):
    SECRET=b"only-a-test-provider-shared-message-proof-key"
    def __init__(self,probe: Probe,tokens: TokenProvider): self.probe,self.tokens=probe,tokens
    @classmethod
    def sign(cls,value):
        data=json.dumps(value,sort_keys=True,separators=(",",":")).encode()
        return base64.b64encode(data)+b"."+hmac.new(cls.SECRET,data,hashlib.sha256).hexdigest().encode()
    @classmethod
    def parse(cls,proof):
        encoded,signature=proof.split(b".")
        data=base64.b64decode(encoded,validate=True)
        if not hmac.compare_digest(hmac.new(cls.SECRET,data,hashlib.sha256).hexdigest().encode(),signature): raise SecurityException("invalid")
        return json.loads(data)
    async def issue_workload(self,identity,payload,*,audience,capability):
        if capability not in identity.capabilities: raise SecurityException("denied")
        value=identity.model_dump(mode="json"); value["audience"]=audience
        return self.sign(dict(identity=value,capability=capability,body=hashlib.sha256(payload).hexdigest()))
    async def verify_workload(self,proof,payload,*,application_id,domain,audience):
        if self.probe.auth_failure: raise SecurityException("unavailable")
        if self.probe.revoked: raise SecurityException("revoked")
        value=self.parse(proof)
        if value["body"]!=hashlib.sha256(payload).hexdigest(): raise SecurityException("invalid")
        identity=WorkloadIdentity.model_validate_json(json.dumps(value["identity"]))
        if (identity.application_id,identity.domain,identity.audience)!=(application_id,domain,audience): raise SecurityException("invalid")
        if identity.service_id!="mq-test" or value["capability"]!="mq:test": raise SecurityException("denied")
        return WorkloadMessage(identity=identity,capability=value["capability"])
    async def issue(self,session,payload,*,audience):
        return self.sign(dict(session=session.model_dump(mode="json"),body=hashlib.sha256(payload).hexdigest(),audience=audience))
    async def verify(self,proof,payload,*,application_id,domain,audience):
        value=self.parse(proof)
        if value["body"]!=hashlib.sha256(payload).hexdigest() or value["audience"]!=audience: raise SecurityException("invalid")
        current=await self.tokens.resolve(value["session"]["token_digest"],application_id=application_id,domain=domain)
        if current is None or current.model_dump(mode="json")!=value["session"]: raise SecurityException("invalid")
        return current
"""


class MQCase(SimpleNamespace):
    async def publish(
        self,
        value,
        *,
        behavior="ok",
        message_id=None,
        tenant_id=None,
        secret="sensitive-mq-payload",
    ):
        async def send():
            token = self.module.producer_tag.set("producer-only")
            try:
                return await self.service.publish(
                    PublishCommand(
                        self.module.definition.destination,
                        self.module.definition.mode,
                        self.module.Payload(value=value, behavior=behavior, secret=secret),
                        message_id=message_id,
                        capability="mq:test",
                    )
                )
            finally:
                self.module.producer_tag.reset(token)

        return await self.app.state.security.run_workload(
            "mq-test", send, capability="mq:test", tenant_id=tenant_id
        )

    async def prepare(self, value, *, behavior="ok", message_id=None, tenant_id=None):
        return await self.app.state.security.run_workload(
            "mq-test",
            lambda: self.service.prepare(
                PublishCommand(
                    "events",
                    self.module.definition.mode,
                    self.module.Payload(value=value, behavior=behavior),
                    message_id=message_id,
                    capability="mq:test",
                )
            ),
            capability="mq:test",
            tenant_id=tenant_id,
        )

    async def until(self, predicate, seconds=10):
        async with asyncio.timeout(seconds):
            while not predicate():
                self.probe.changed.clear()
                if predicate():
                    break
                await self.probe.changed.wait()


@pytest.fixture
def mq_backend(request):
    return getattr(request, "param", "stream")


@pytest.fixture
def mq_options(request):
    return getattr(request, "param", {})


@pytest.fixture
async def mq_case(mq_backend, mq_options, module_package, config_dir, tmp_path):
    targets = json.loads(os.environ.get("DUSHAN_MQ_TARGETS", "{}"))
    if "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("真实 Redis 实例未配置")
    if mq_backend in {"rabbitmq", "kafka"} and mq_backend not in targets:
        pytest.skip(f"真实 {mq_backend} 实例未配置")
    mode = {"stream": "stream", "pubsub": "pubsub", "rabbitmq": "queue", "kafka": "topic"}[
        mq_backend
    ]
    suffix = uuid4().hex[:10]
    package = "mq_case_" + suffix
    source = SOURCE.replace("__MODE__", mode).replace(
        "__GROUP__", repr("test-group") if mode in {"stream", "topic"} else "None"
    )
    source = source.replace(
        "__RETRIES__", str(mq_options.get("retries", 0 if mode == "pubsub" else 2))
    )
    source = source.replace(
        "__EXHAUSTED__",
        mq_options.get("exhausted", "discard" if mode == "pubsub" else "dead_letter"),
    )
    source = source.replace("__TENANT__", "global")
    source = source.replace("__EXTERNAL__", "External" if mq_options.get("external") else "None")
    source = source.replace("__SQL_QUERY__", "")
    if mq_options.get("second_consumer"):
        source += """
from dataclasses import replace
second_definition=replace(definition,key="secondary",destination="other",group="secondary-workers" if definition.group else None)
@consumer(second_definition)
class Secondary(Controlled):
    pass
"""
    if "delay" in mq_options:
        source = source.replace(
            "delay_seconds=0.2,backoff=2,max_delay_seconds=0.8",
            f"delay_seconds={mq_options['delay']},backoff=2,max_delay_seconds={mq_options['delay'] * 4}",
        )
    module_package(package, name=package, scan_roots=(".",), files={"components.py": source})
    module = importlib.import_module(package + ".components")
    mq_values = {
        "enabled": True,
        "backend": "redis" if mode in {"stream", "pubsub"} else mq_backend,
        "namespace": "m" + suffix,
        "signing_secret": "mq-test-only-framework-signing-key-7a91",
        "command_timeout_seconds": 10.0,
        "lease_seconds": 20.0,
        "renew_seconds": 0.2,
        "handler_timeout_seconds": 5.0,
        "shutdown_seconds": 0.2,
        "poll_seconds": 0.02,
        "concurrency": 2,
        "prefetch": 4,
        "stream_max_length": 50,
        "retry_max_length": 20,
        "dead_letter_max_length": 20,
    }
    if mq_backend == "rabbitmq":
        mq_values["rabbit_url"] = targets["rabbitmq"]
    elif mq_backend == "kafka":
        mq_values["kafka_bootstrap_servers"] = targets["kafka"]
    mq_values.update(mq_options.get("settings", {}))
    values = {
        "banner": {"enabled": False},
        "modules": {"packages": ["framework", package], "enabled": ["framework", package]},
        "config": {
            "models": {
                "security": {"enabled": True},
                "cache": {"enabled": True, "port": int(os.environ["DUSHAN_DP_REDIS_PORT"])},
                "mq": mq_values,
            }
        },
    }
    path = config_dir(values)
    async with AsyncExitStack() as stack:

        async def open_app(base):
            app = create_app(base_dir=base, environ={})
            await stack.enter_async_context(app.router.lifespan_context(app))
            await app.state.mq.wait_ready()
            with app.state.application_context.execution():
                service = app.state.application_context.container.get(MQService)
                probe = app.state.application_context.container.get(module.Probe)
            return MQCase(
                app=app, runtime=app.state.mq, service=service, probe=probe, module=module
            )

        case = await open_app(path)

        async def peer(**changes):
            peer_values = ConfigFactory.values()
            ConfigFactory.merge(peer_values, values)
            peer_values["log"]["enable_file_overall"] = False
            ConfigFactory.merge(peer_values, changes)
            peer_path = tmp_path / ("peer_" + uuid4().hex[:8])
            peer_path.mkdir()
            (peer_path / "application.yaml").write_text(
                yaml.safe_dump(peer_values, allow_unicode=True), encoding="utf-8"
            )
            result = await open_app(peer_path)
            result.probe.changed = case.probe.changed
            return result

        case.peer = peer
        case.configuration = values
        case.config_path = path
        yield case
    assert case.runtime.resources()["inflight"] == 0
    assert case.runtime.resources()["active_consumers"] == 0


def remove_classes(source, names):
    lines = source.splitlines()
    removed = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name in names:
            start = min(node.lineno, *(item.lineno for item in node.decorator_list))
            removed.update(range(start - 1, node.end_lineno))
    return "\n".join(line for index, line in enumerate(lines) if index not in removed)


@pytest.fixture(params=TARGETS, ids=lambda target: target["name"])
def mq_sql_target(request):
    return request.param


@pytest.fixture
def mq_sql_options(request):
    return getattr(request, "param", {})


@pytest.fixture
async def mq_sql_case(mq_sql_target, mq_sql_options, config_dir, module_package, tmp_path):
    from starter_job.conftest import SOURCE as JOB_SOURCE
    from starter_tenant.conftest import SOURCE as TENANT_SOURCE

    from starter_mq.sql_provider_source import SOURCE as OUTBOX_SOURCE

    if "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("真实 Redis 实例未配置")
    suffix = uuid4().hex[:10]
    job_package, mq_package, store_package, tenant_package = (
        kind + suffix for kind in ("mj_", "mm_", "mo_", "mt_")
    )
    permissions = mq_sql_options.get("permissions", False)
    session_mode = mq_sql_options.get("session", False)
    job_source = remove_classes(
        JOB_SOURCE.format(suffix=suffix), {"Tokens", "Permissions", "Workloads"}
    )
    if permissions:
        job_source = (
            "from framework.starter_data_permission.decorators.data_permission import public_data\n"
            + job_source.replace("@global_model", "@public_data(tenant_column=None)\n@global_model")
        )
    module_package(
        job_package, name=job_package, scan_roots=(".",), files={"components.py": job_source}
    )
    job_module = importlib.import_module(job_package + ".components")
    tenant_module = None
    if mq_sql_options.get("tenant"):
        tenant_source = remove_classes(
            TENANT_SOURCE.format(
                suffix="mq" + suffix,
                public="@public_data(tenant_column=None)" if permissions else "",
                protected='@data_permission(membership_column="membership_id", department_column="dept_id")'
                if permissions
                else "",
            ),
            {"Workloads"} if session_mode else {"Tokens", "Permissions", "Workloads"},
        )
        tenant_source = tenant_source.replace('"maintenance"', '"mq-test"').replace(
            '"records:maintain"', '"mq:test"'
        )
        module_package(
            tenant_package,
            name=tenant_package,
            scan_roots=(".",),
            files={"components.py": tenant_source},
        )
        tenant_module = importlib.import_module(tenant_package + ".components")
    source = (
        SOURCE.replace("__MODE__", "stream")
        .replace("__GROUP__", '"workers"')
        .replace("__RETRIES__", "1")
        .replace("__EXHAUSTED__", "dead_letter")
        .replace("__EXTERNAL__", "None")
    )
    source = source.replace("__TENANT__", "required" if tenant_module is not None else "global")
    if session_mode:
        source = remove_classes(source, {"Tokens", "Permissions"})
        source = source.replace(
            "session_policy=None",
            'session_policy=RoutePolicy(tenant_required=True,permissions=("read",))',
        )
    query = ""
    if tenant_module is not None:
        query = f"""from {tenant_package}.components import Record
        from sqlalchemy import select
        from framework.starter_di.context.get_bean import get_bean
        from framework.starter_database.session.session_provider import SessionProvider
        database=get_bean(SessionProvider)
        async with database.read_session() as session:
            visible=list((await session.scalars(select(Record.__table__.c.tenant_id).where(Record.value>0))).all())
        self.probe.visible.append((context.tenant_id,visible))"""
    source = source.replace("__SQL_QUERY__", query)
    module_package(mq_package, name=mq_package, scan_roots=(".",), files={"components.py": source})
    mq_module = importlib.import_module(mq_package + ".components")
    store_source = OUTBOX_SOURCE.replace("__SUFFIX__", suffix)
    if permissions:
        store_source = (
            "from framework.starter_data_permission.decorators.data_permission import public_data\n"
            + store_source.replace(
                "@global_model", "@public_data(tenant_column=None)\n@global_model"
            )
        )
    module_package(
        store_package, name=store_package, scan_roots=(".",), files={"components.py": store_source}
    )
    store_module = importlib.import_module(store_package + ".components")
    url = mq_sql_target["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'mq.sqlite').as_posix()}"
    database_values = {
        **ConfigFactory.values()["config"]["models"]["database"],
        "enabled": True,
        "health_check_enabled": False,
        "sources": [dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)],
    }
    engine = create_async_engine(url)
    metadata = [job_module.metadata, store_module.metadata]
    packages = ["framework", job_package, mq_package, store_package]
    if tenant_module is not None:
        metadata.append(tenant_module.metadata)
        packages.append(tenant_package)
    try:
        async with engine.begin() as connection:
            for item in metadata:
                await connection.run_sync(item.create_all)
            now = datetime.now(UTC).replace(tzinfo=None)
            audit = dict(create_time=now, update_time=now)
            await connection.execute(
                insert(job_module.Control.__table__).values(id=1, dirty=False, **audit)
            )
            await connection.execute(
                insert(store_module.Control.__table__).values(id=1, label="outbox", **audit)
            )
            if tenant_module is not None:
                await connection.execute(
                    insert(tenant_module.Directory.__table__),
                    [
                        dict(id=1, tenant_key="1", enabled=True, **audit),
                        dict(id=2, tenant_key="2", enabled=True, **audit),
                    ],
                )
                await connection.execute(
                    insert(tenant_module.Record.__table__),
                    [
                        dict(
                            id=1,
                            tenant_id="1",
                            membership_id="m1",
                            dept_id="d1",
                            name="one",
                            value=1,
                            **audit,
                        ),
                        dict(
                            id=2,
                            tenant_id="2",
                            membership_id="m2",
                            dept_id="d2",
                            name="two",
                            value=2,
                            **audit,
                        ),
                        dict(
                            id=3,
                            tenant_id="1",
                            membership_id="m2",
                            dept_id="d1",
                            name="other",
                            value=3,
                            **audit,
                        ),
                    ],
                )
                await connection.execute(
                    insert(tenant_module.Member.__table__),
                    [
                        dict(
                            id=1,
                            tenant_key="1",
                            member_key="m1",
                            account="account-m1",
                            department="d1",
                            enabled=True,
                            **audit,
                        ),
                        dict(
                            id=2,
                            tenant_key="1",
                            member_key="m2",
                            account="account-m2",
                            department="d1",
                            enabled=True,
                            **audit,
                        ),
                    ],
                )
        configuration = {
            "banner": {"enabled": False},
            "modules": {"packages": packages, "enabled": packages},
            "config": {
                "models": {
                    "database": database_values,
                    "security": {"enabled": True},
                    "data_permission": {"enabled": permissions},
                    "cache": {"enabled": True, "port": int(os.environ["DUSHAN_DP_REDIS_PORT"])},
                    "job": {
                        "enabled": True,
                        "owner_enabled": True,
                        "namespace": "j" + suffix,
                        "poll_seconds": 0.02,
                        "reconciliation_seconds": 0.2,
                        "shutdown_seconds": 0.2,
                    },
                    "mq": {
                        "enabled": True,
                        "namespace": "q" + suffix,
                        "signing_secret": "mq-sql-test-only-framework-signing-key",
                        "outbox_enabled": True,
                        "outbox_retry_seconds": 0.1,
                        "outbox_batch_size": 10,
                        "concurrency": 2,
                        "prefetch": 4,
                        "poll_seconds": 0.02,
                        "shutdown_seconds": 0.2,
                        "stream_max_length": mq_sql_options.get("capacity", 50),
                    },
                }
            },
        }
        path = config_dir(configuration)
        app = create_app(base_dir=path, environ={})
        async with app.router.lifespan_context(app):
            await app.state.mq.wait_ready()
            with app.state.application_context.execution():
                from framework.starter_security.spi.token_provider import TokenProvider

                container = app.state.application_context.container
                case = MQCase(
                    app=app,
                    runtime=app.state.mq,
                    service=container.get(MQService),
                    outbox=container.get(OutboxService),
                    store=container.get(OutboxProvider),
                    probe=container.get(mq_module.Probe),
                    module=mq_module,
                    store_module=store_module,
                    engine=engine,
                    job=container.get(JobService),
                    job_module=job_module,
                    tenant_module=tenant_module,
                    database=app.state.database,
                    tokens=container.get(TokenProvider),
                )
            yield case
    finally:
        async with engine.begin() as connection:
            for item in reversed(metadata):
                await connection.run_sync(item.drop_all)
        await engine.dispose()
