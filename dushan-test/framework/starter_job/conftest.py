import ast
import importlib
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from framework.starter_job.core.job_service import JobService
from framework.starter_job.model.job_definition import JobDefinition
from server.starter_server import create_app

SOURCE = """
import asyncio
import json
import threading
from datetime import UTC, datetime, timedelta
from pydantic import BaseModel
from sqlalchemy import MetaData, String, Boolean, JSON, DateTime, select, insert, update, delete, func
from sqlalchemy.orm import mapped_column
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_job.decorators.job import job
from framework.starter_job.handler.job_handler import JobHandler
from framework.starter_job.model.job_definition import JobDefinition
from framework.starter_job.model.job_request import JobRequest
from framework.starter_job.definitions.enums.job_trigger_kind import JobTriggerKind
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.spi.job_definition_provider import JobDefinitionProvider
from framework.starter_job.spi.job_request_provider import JobRequestProvider
from framework.starter_job.spi.job_record_provider import JobRecordProvider
from framework.starter_job.spi.tenant_job_target_provider import TenantJobTargetProvider
from framework.starter_job.model.tenant_job_lease import TenantJobLease
from framework.starter_job.exception.job_result_unknown import JobResultUnknown
from framework.starter_di.context.get_bean import get_bean
from framework.starter_tenant.context.tenant_context import TenantContext
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_job.core.job_service import JobService
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes

metadata=MetaData()
@global_model
class Plan(BaseDO):
    __tablename__="job_plan_{suffix}"
    metadata=metadata
    job_key=mapped_column(String(128),unique=True,nullable=False)
    spec=mapped_column(JSON,nullable=False)
@global_model
class RequestRow(BaseDO):
    __tablename__="job_request_{suffix}"
    metadata=metadata
    request_key=mapped_column(String(128),unique=True,nullable=False)
    job_key=mapped_column(String(128),nullable=False)
    spec=mapped_column(JSON,nullable=False)
    ready_at=mapped_column(DateTime,nullable=False)
    owner=mapped_column(String(64),nullable=True)
    state=mapped_column(String(32),nullable=False)
@global_model
class Cursor(BaseDO):
    __tablename__="job_cursor_{suffix}"
    metadata=metadata
    job_key=mapped_column(String(128),unique=True,nullable=False)
    at=mapped_column(DateTime,nullable=False)
@global_model
class Control(BaseDO):
    __tablename__="job_control_{suffix}"
    metadata=metadata
    dirty=mapped_column(Boolean,nullable=False)
@global_model
class RecordRow(BaseDO):
    __tablename__="job_record_{suffix}"
    metadata=metadata
    spec=mapped_column(JSON,nullable=False)
@global_model
class TargetRow(BaseDO):
    __tablename__="job_target_{suffix}"
    metadata=metadata
    target_key=mapped_column(String(200),unique=True,nullable=False)
    token=mapped_column(String(64),nullable=False)
    expires=mapped_column(DateTime,nullable=False)
    state=mapped_column(String(32),nullable=False)

@service
class Probe:
    def __init__(self):
        self.active=0
        self.peak=0
        self.runs=[]
        self.tenants=[]
        self.entered=asyncio.Event()
        self.release=asyncio.Event()
        self.thread_entered=threading.Event()
        self.thread_release=threading.Event()
        self.record_failure=False
        self.definition_failure=False
        self.claim_wait=None
        self.claimed=asyncio.Event()
        self.settlement_failure=False

class Parameters(BaseModel):
    mode: str="success"

@job(key="controlled",parameters=Parameters,source="controlled-job",capability="test:execute")
class Controlled(JobHandler):
    def __init__(self,probe: Probe): self.probe=probe
    async def execute(self,parameters,context):
        self.probe.active+=1
        self.probe.peak=max(self.probe.peak,self.probe.active)
        self.probe.runs.append((context.request_id,context.attempt))
        self.probe.tenants.append(context.tenant_id)
        if context.tenant_id is not None: assert get_bean(TenantContext).get_required_tenant_id()==context.tenant_id
        self.probe.entered.set()
        try:
            if parameters.mode=="wait": await self.probe.release.wait()
            if parameters.mode=="unknown": raise JobResultUnknown("unknown effect")
            if parameters.mode=="fail" or parameters.mode=="retry" and context.attempt==1: raise ValueError("controlled failure")
            return "done"
        finally: self.probe.active-=1
    async def pre_execute(self,context): return context.job_id != "skip"

@job(key="blocking",parameters=Parameters,source="controlled-job",capability="test:execute")
class Blocking(JobHandler):
    def __init__(self,probe: Probe): self.probe=probe
    def execute(self,parameters,context):
        self.probe.thread_entered.set()
        self.probe.thread_release.wait(5)
        return "thread-done"

@service(interface=TokenProvider)
class Tokens(TokenProvider):
    async def resolve(self,*args,**kwargs): return None
@service(interface=PermissionProvider)
class Permissions(PermissionProvider):
    async def snapshot(self,*args,**kwargs): raise SecurityException(SecurityErrorCodes.DENIED)
@service(interface=WorkloadProvider)
class Workloads(WorkloadProvider):
    async def authenticate(self,source,*,application_id,domain,capability,tenant_id):
        if source!="controlled-job" or capability!="test:execute" or tenant_id not in (None,"1","2"): raise SecurityException(SecurityErrorCodes.DENIED)
        return WorkloadIdentity(application_id=application_id,domain=domain,service_id="test-worker",tenant_id=tenant_id,audience=source,capabilities=frozenset((capability,)),expires_at=datetime.now(UTC)+timedelta(minutes=5))

@service(interface=JobDefinitionProvider)
class Definitions(JobDefinitionProvider):
    def __init__(self,database: SessionProvider,probe: Probe): self.database,self.probe=database,probe
    async def list_definitions(self):
        if self.probe.definition_failure: raise RuntimeError("definition read failed")
        async with self.database.read_session(force_primary=True) as session:
            values=(await session.scalars(select(Plan.spec))).all()
        return tuple(JobDefinition.model_validate_json(json.dumps(value)) for value in values)
    async def get_definition(self,job_id):
        async with self.database.read_session(force_primary=True) as session:
            value=await session.scalar(select(Plan.spec).where(Plan.job_key==job_id))
        return None if value is None else JobDefinition.model_validate_json(json.dumps(value))
    async def save_definition(self,definition):
        async with self.database.transaction() as session:
            present=await session.scalar(select(Plan.id).where(Plan.job_key==definition.id))
            if present is None: await session.execute(insert(Plan).values(job_key=definition.id,spec=definition.model_dump(mode="json")))
            else: await session.execute(update(Plan).where(Plan.id==present).values(spec=definition.model_dump(mode="json")))
    async def delete_definition(self,job_id):
        async with self.database.transaction() as session: await session.execute(delete(Plan).where(Plan.job_key==job_id))
    async def stop_definition(self,job_id,revision):
        async with self.database.transaction() as session:
            row=(await session.execute(select(Plan.id,Plan.spec).where(Plan.job_key==job_id).with_for_update())).one_or_none()
            if row is not None and row.spec["revision"]==revision:
                value=dict(row.spec)
                value["enabled"]=False
                await session.execute(update(Plan).where(Plan.id==row.id).values(spec=value))

@service(interface=JobRequestProvider)
class Requests(JobRequestProvider):
    def __init__(self,database: SessionProvider,probe: Probe): self.database,self.probe=database,probe
    async def submit(self,request,*,pending_limit):
        async with self.database.transaction() as session:
            await session.execute(select(Control.id).where(Control.id==1).with_for_update())
            if await session.scalar(select(RequestRow.id).where(RequestRow.request_key==request.request_id)) is not None: return False
            if await session.scalar(select(func.count()).select_from(RequestRow).where(RequestRow.state=="pending"))>=pending_limit: raise JobException(JobErrorCodes.CAPACITY)
            await session.execute(insert(RequestRow).values(request_key=request.request_id,job_key=request.definition.id,spec=request.model_dump(mode="json"),ready_at=request.ready_at.astimezone(UTC).replace(tzinfo=None),owner=None,state="pending"))
            if request.trigger is JobTriggerKind.SCHEDULED:
                cursor=await session.scalar(select(Cursor.id).where(Cursor.job_key==request.definition.id))
                values=dict(at=request.scheduled_at.astimezone(UTC).replace(tzinfo=None))
                if cursor is None: await session.execute(insert(Cursor).values(job_key=request.definition.id,**values))
                else: await session.execute(update(Cursor).where(Cursor.id==cursor).values(**values))
        return True
    async def checkpoint(self,job_id):
        async with self.database.read_session(force_primary=True) as session:
            value=await session.scalar(select(Cursor.at).where(Cursor.job_key==job_id))
        return None if value is None else value.replace(tzinfo=UTC)
    async def claim(self,owner,*,exclude_jobs,now):
        async with self.database.transaction() as session:
            await session.execute(select(Control.id).where(Control.id==1).with_for_update())
            query=select(RequestRow).where(RequestRow.state=="pending",RequestRow.ready_at<=now.astimezone(UTC).replace(tzinfo=None))
            if exclude_jobs: query=query.where(RequestRow.job_key.not_in(exclude_jobs))
            row=(await session.scalars(query.order_by(RequestRow.id).limit(1).with_for_update())).one_or_none()
            if row is None: return None
            await session.execute(update(RequestRow).where(RequestRow.id==row.id).values(owner=owner,state="running"))
            request=JobRequest.model_validate_json(json.dumps(row.spec))
        self.probe.claimed.set()
        if self.probe.claim_wait is not None: await self.probe.claim_wait.wait()
        return request
    async def finish(self,request_id,owner,state):
        async with self.database.transaction() as session:
            result=await session.execute(update(RequestRow).where(RequestRow.request_key==request_id,RequestRow.owner==owner,RequestRow.state=="running").values(state=state.value))
            if result.rowcount!=1: raise RuntimeError("request owner mismatch")
    async def retry(self,request,owner):
        async with self.database.transaction() as session:
            result=await session.execute(update(RequestRow).where(RequestRow.request_key==request.request_id,RequestRow.owner==owner,RequestRow.state=="running").values(spec=request.model_dump(mode="json"),ready_at=request.ready_at.astimezone(UTC).replace(tzinfo=None),owner=None,state="pending"))
            if result.rowcount!=1: raise RuntimeError("request owner mismatch")
    async def notify_changed(self):
        async with self.database.transaction() as session: await session.execute(update(Control).where(Control.id==1).values(dirty=True))
    async def consume_changes(self):
        async with self.database.transaction() as session:
            value=await session.scalar(select(Control.dirty).where(Control.id==1).with_for_update())
            if value: await session.execute(update(Control).where(Control.id==1).values(dirty=False))
            return value

@service(interface=JobRecordProvider)
class Records(JobRecordProvider):
    def __init__(self,database: SessionProvider,probe: Probe): self.database,self.probe=database,probe
    async def record(self,record):
        if self.probe.record_failure: raise RuntimeError("record failed")
        async with self.database.transaction() as session:
            await session.execute(insert(RecordRow).values(spec=record.model_dump(mode="json")))

@controller("/test-jobs",policy=RoutePolicy.public())
class TestController:
    def __init__(self,jobs: JobService): self.jobs=jobs
    @route("/trigger",methods=("POST",))
    async def trigger(self): return dict(requestId=await self.jobs.trigger("job"))

@service(interface=TenantJobTargetProvider)
class Targets(TenantJobTargetProvider):
    def __init__(self,database: SessionProvider,probe: Probe): self.database,self.probe=database,probe
    async def claim(self,request_id,tenant_id,lease_seconds):
        from uuid import uuid4
        key=request_id+":"+tenant_id
        token=uuid4().hex
        expiry=datetime.now(UTC)+timedelta(seconds=lease_seconds)
        async with self.database.transaction() as session:
            await session.execute(select(Control.id).where(Control.id==1).with_for_update())
            row=(await session.scalars(select(TargetRow).where(TargetRow.target_key==key))).one_or_none()
            if row is not None:
                if row.state=="completed": return None
                if row.state=="running":
                    if row.expires < datetime.now(UTC).replace(tzinfo=None): raise RuntimeError("stalled target requires reconciliation")
                    return None
                await session.execute(update(TargetRow).where(TargetRow.id==row.id).values(token=token,expires=expiry.replace(tzinfo=None),state="running"))
            else:
                await session.execute(insert(TargetRow).values(target_key=key,token=token,expires=expiry.replace(tzinfo=None),state="running"))
        return TenantJobLease(request_id=request_id,tenant_id=tenant_id,token=token,expires_at=expiry)
    async def complete(self,lease):
        if self.probe.settlement_failure: raise RuntimeError("settlement unavailable")
        async with self.database.transaction() as session:
            result=await session.execute(update(TargetRow).where(TargetRow.target_key==lease.request_id+":"+lease.tenant_id,TargetRow.token==lease.token,TargetRow.state=="running",TargetRow.expires>datetime.now(UTC).replace(tzinfo=None)).values(state="completed"))
            if result.rowcount!=1: raise RuntimeError("target lease lost")
    async def release(self,lease):
        async with self.database.transaction() as session:
            result=await session.execute(update(TargetRow).where(TargetRow.target_key==lease.request_id+":"+lease.tenant_id,TargetRow.token==lease.token,TargetRow.state=="running").values(state="ready"))
            if result.rowcount!=1: raise RuntimeError("target lease lost")
"""


class JobCase(SimpleNamespace):
    def definition(self, job_id="job", **changes):
        values = dict(
            id=job_id,
            handler_key="controlled",
            parameters={"mode": "success"},
            cron="0 0 1 1 *",
            enabled=True,
            revision=uuid4().hex,
            effective_at=datetime.now(UTC),
            max_instances=1,
            timeout_seconds=5.0,
            max_retries=0,
            retry_seconds=0.1,
            retry_backoff=2.0,
            stop_after_failure=False,
            tenant_id=None,
            fan_out=False,
        )
        values.update(changes)
        return JobDefinition.model_validate(values)


@pytest.fixture(params=TARGETS, ids=lambda target: target["name"])
def job_target(request):
    return request.param


@pytest.fixture
async def job_case(job_target, config_dir, module_package, tmp_path, request):
    options = getattr(request, "param", {})
    suffix = uuid4().hex[:12]
    package = "job_case_" + suffix
    module_package(
        package,
        name=package,
        scan_roots=(".",),
        files={"components.py": SOURCE.format(suffix=suffix)},
    )
    module = importlib.import_module(package + ".components")
    tenant_module = None
    tenant_package = None
    if options.get("tenant"):
        from starter_tenant.conftest import SOURCE as TENANT_SOURCE

        tenant_package = "job_tenants_" + suffix
        tenant_source = TENANT_SOURCE.format(suffix="jt_" + suffix, public="", protected="")
        lines = tenant_source.splitlines()
        remove = set()
        for node in ast.parse(tenant_source).body:
            if isinstance(node, ast.ClassDef) and node.name in {
                "Tokens",
                "Permissions",
                "Workloads",
            }:
                start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
                remove.update(range(start - 1, node.end_lineno))
        tenant_source = (
            "\n".join(line for index, line in enumerate(lines) if index not in remove)
            .replace('"maintenance"', '"test-worker"')
            .replace('"records:maintain"', '"test:execute"')
        )
        module_package(
            tenant_package,
            name=tenant_package,
            scan_roots=(".",),
            files={"components.py": tenant_source},
        )
        tenant_module = importlib.import_module(tenant_package + ".components")
    url = job_target["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'job.sqlite').as_posix()}"
    values = {
        **ConfigFactory.values()["config"]["models"]["database"],
        "enabled": True,
        "health_check_enabled": False,
        "sources": [dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)],
    }
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.create_all)
            if tenant_module is not None:
                await connection.run_sync(tenant_module.metadata.create_all)
            now = datetime.now(UTC).replace(tzinfo=None)
            await connection.execute(
                insert(module.Control.__table__).values(
                    id=1, dirty=False, create_time=now, update_time=now
                )
            )
            if tenant_module is not None:
                await connection.execute(
                    insert(tenant_module.Directory.__table__),
                    [
                        dict(id=1, tenant_key="1", enabled=True, create_time=now, update_time=now),
                        dict(id=2, tenant_key="2", enabled=True, create_time=now, update_time=now),
                    ],
                )
        configuration = {
            "banner": {"enabled": False},
            "modules": {"packages": ["framework", package], "enabled": ["framework", package]},
            "config": {
                "models": {
                    "database": values,
                    "security": {"enabled": True},
                    "cache": {"enabled": True, "port": int(os.environ["DUSHAN_DP_REDIS_PORT"])},
                    "job": {
                        "enabled": True,
                        "owner_enabled": options.get("owner", True),
                        "namespace": "j" + suffix,
                        "timezone": "UTC",
                        "poll_seconds": 0.01,
                        "reconciliation_seconds": 0.2,
                        "command_timeout_seconds": 5.0,
                        "owner_lease_seconds": 10.0,
                        "owner_renew_seconds": 0.2,
                        "shutdown_seconds": 0.2,
                        "pending_limit": options.get("capacity", 30),
                    },
                }
            },
        }
        if tenant_package is not None:
            configuration["modules"]["packages"].append(tenant_package)
            configuration["modules"]["enabled"].append(tenant_package)
        path = config_dir(configuration)
        app = create_app(base_dir=path, environ={})
        async with app.router.lifespan_context(app):
            with app.state.application_context.execution():
                service = app.state.application_context.container.get(JobService)
                probe = app.state.application_context.container.get(module.Probe)
            yield JobCase(
                app=app,
                runtime=app.state.job,
                service=service,
                probe=probe,
                module=module,
                engine=engine,
                config_path=path,
                configuration=configuration,
            )
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.drop_all)
            if tenant_module is not None:
                await connection.run_sync(tenant_module.metadata.drop_all)
        await engine.dispose()
