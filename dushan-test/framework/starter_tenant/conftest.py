import importlib
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app

SOURCE = """
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from sqlalchemy import MetaData, String, Integer, BigInteger, Boolean, ForeignKeyConstraint, UniqueConstraint, select, insert
from sqlalchemy.orm import mapped_column
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_tenant.decorators.tenant_model import tenant_model, global_model
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_info import TenantInfo
from framework.starter_tenant.model.tenant_resource_grant import TenantResourceGrant
from framework.starter_tenant.model.tenant_access_grant import TenantAccessGrant
from framework.starter_tenant.spi.tenant_directory_provider import TenantDirectoryProvider
from framework.starter_tenant.spi.tenant_provisioning_provider import TenantProvisioningProvider
from framework.starter_tenant.model.tenant_provisioning_result import TenantProvisioningResult
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from framework.starter_security.model.workload_identity import WorkloadIdentity
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_di.decorators.conditional import conditional
from framework.starter_tenant.config.tenant_settings import TenantSettings
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_data_permission.decorators.data_permission import data_permission, public_data
from framework.starter_data_permission.spi.data_permission_provider import DataPermissionProvider
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_data_permission.enums.data_scope import DataScope

metadata = MetaData()

{public}
@global_model
class Directory(BaseDO):
    __tablename__ = "tenant_directory_{suffix}"
    metadata = metadata
    tenant_key = mapped_column(String(64), nullable=False, unique=True)
    enabled = mapped_column(Boolean, nullable=False)

{public}
@global_model
class Member(BaseDO):
    __tablename__ = "tenant_member_{suffix}"
    metadata = metadata
    tenant_key = mapped_column(String(64), nullable=False)
    member_key = mapped_column(String(64), nullable=False)
    account = mapped_column(String(64), nullable=False)
    department = mapped_column(String(64), nullable=False)
    enabled = mapped_column(Boolean, nullable=False)

{public}
@global_model
class Receipt(BaseDO):
    __tablename__ = "tenant_receipt_{suffix}"
    metadata = metadata
    __table_args__ = (UniqueConstraint("account","request_key"),UniqueConstraint("tenant_key"))
    account = mapped_column(String(64),nullable=False)
    request_key = mapped_column(String(128),nullable=False)
    tenant_key = mapped_column(String(64),nullable=False)
    member_key = mapped_column(String(64),nullable=False)
    requested_name = mapped_column(String(200),nullable=False)

{public}
@global_model
class AccessApproval(BaseDO):
    __tablename__ = "tenant_approval_{suffix}"
    metadata = metadata
    kind = mapped_column(String(32),nullable=False)
    actor = mapped_column(String(128),nullable=False)
    tenant_key = mapped_column(String(64),nullable=False)
    reference = mapped_column(String(128),nullable=False)
    resource = mapped_column(String(200),nullable=False)
    enabled = mapped_column(Boolean,nullable=False)

{protected}
@tenant_model()
class Record(BaseDO):
    __tablename__ = "tenant_record_{suffix}"
    metadata = metadata
    __table_args__ = (UniqueConstraint("tenant_id", "name"), UniqueConstraint("tenant_id", "id"))
    tenant_id = mapped_column(String(64), nullable=False)
    membership_id = mapped_column(String(64), nullable=False)
    dept_id = mapped_column(String(64), nullable=False)
    name = mapped_column(String(64), nullable=False)
    value = mapped_column(Integer, nullable=False)

{protected}
@tenant_model()
class Child(BaseDO):
    __tablename__ = "tenant_child_{suffix}"
    metadata = metadata
    __table_args__ = (ForeignKeyConstraint(["tenant_id", "parent_id"], ["tenant_record_{suffix}.tenant_id", "tenant_record_{suffix}.id"], ondelete="CASCADE"),)
    tenant_id = mapped_column(String(64), nullable=False)
    membership_id = mapped_column(String(64), nullable=False)
    dept_id = mapped_column(String(64), nullable=False)
    parent_id = mapped_column(BigInteger, nullable=False)
    name = mapped_column(String(64), nullable=False)

@service(interface=TokenProvider)
class Tokens(TokenProvider):
    def __init__(self): self.sessions = dict()
    async def resolve(self, digest, **kwargs): return self.sessions.get(digest)
    async def revoke(self, identity):
        self.sessions[identity.token_digest] = identity.model_copy(update=dict(revoked=True))

@service(interface=PermissionProvider)
class Permissions(PermissionProvider):
    async def snapshot(self, identity, *, binding):
        return PermissionSnapshot(binding=binding, revision=identity.authorization_revision,
            permissions=frozenset(("read", "write")), roles=frozenset())

@service(interface=WorkloadProvider)
class Workloads(WorkloadProvider):
    def __init__(self): self.credential_valid = True
    async def authenticate(self, source, *, application_id, domain, capability, tenant_id):
        if not self.credential_valid or source != "maintenance" or capability != "records:maintain" or tenant_id not in (None,"1","2") or application_id != "dushan-ai-native" or domain != "admin":
            raise SecurityException("denied")
        return WorkloadIdentity(application_id=application_id, domain=domain, service_id="maintenance", tenant_id=tenant_id, audience=source, capabilities=frozenset((capability,)), expires_at=datetime.now(UTC)+timedelta(minutes=5))

@service(interface=TenantDirectoryProvider)
class DirectoryProvider(TenantDirectoryProvider):
    def __init__(self, database: SessionProvider):
        self.database = database
        self.failure = None
        self.actions = frozenset(("select", "insert", "update", "delete"))
    async def get_tenant(self, tenant_id):
        if self.failure is not None: raise self.failure
        async with self.database.read_session(force_primary=True) as session:
            row = (await session.execute(select(Directory.tenant_key, Directory.enabled).where(Directory.tenant_key == tenant_id))).one_or_none()
        return None if row is None else TenantInfo(tenant_id=row.tenant_key, enabled=row.enabled)
    async def authorize_session(self, identity, policy):
        async with self.database.read_session(force_primary=True) as session:
            if identity.realm is SecurityRealm.SUPPORT:
                approval=await session.scalar(select(AccessApproval.id).where(AccessApproval.kind=="support",AccessApproval.actor==identity.platform_operator_id,AccessApproval.tenant_key==identity.tenant_id,AccessApproval.reference==identity.support_session_id,AccessApproval.resource==identity.approved_resource,AccessApproval.enabled.is_(True)))
                if approval is None or identity.approved_action != "read": raise TenantException("denied")
                return TenantAccessGrant(tenant_id=identity.tenant_id,source="approved-support",resources=(TenantResourceGrant(resource=Record.__table__.key,actions=frozenset(("select",))),),expires_at=identity.expires_at)
            if identity.access_mode.value=="group_managed":
                approval=await session.scalar(select(AccessApproval.id).where(AccessApproval.kind=="managed",AccessApproval.actor==identity.authority_tenant_id+":"+identity.authority_membership_id,AccessApproval.tenant_key==identity.tenant_id,AccessApproval.reference==identity.group_id+":"+identity.management_relation_id,AccessApproval.enabled.is_(True)))
                authority=await session.scalar(select(Member.id).where(Member.tenant_key==identity.authority_tenant_id,Member.member_key==identity.authority_membership_id,Member.account==identity.account_id,Member.enabled.is_(True)))
                if approval is None or authority is None: raise TenantException("denied")
                return
            member = await session.scalar(select(Member.id).where(Member.tenant_key == identity.tenant_id, Member.member_key == identity.membership_id, Member.account == identity.account_id, Member.enabled.is_(True)))
        if member is None: raise TenantException("denied")
    async def authorize_workload(self, identity, capability):
        if identity.service_id != "maintenance" or capability != "records:maintain": raise TenantException("denied")
        return TenantAccessGrant(tenant_id=identity.tenant_id, source="verified-maintenance",
            resources=(TenantResourceGrant(resource=Record.__table__.key, actions=self.actions), TenantResourceGrant(resource=Child.__table__.key, actions=self.actions)), expires_at=identity.expires_at)
    async def enabled_tenant_ids(self):
        async with self.database.read_session(force_primary=True) as session:
            return tuple((await session.scalars(select(Directory.tenant_key).where(Directory.enabled.is_(True)).order_by(Directory.tenant_key))).all())

@service(interface=TenantProvisioningProvider)
class Provisioning(TenantProvisioningProvider):
    def __init__(self, database: SessionProvider):
        self.database=database
        self.fail_after_directory=False
    async def provision(self, identity, request, *, fixed_tenant_id):
        async with self.database.transaction() as session:
            old=(await session.execute(select(Receipt).where(Receipt.account==identity.account_id,Receipt.request_key==request.idempotency_key))).scalar_one_or_none()
            if old is not None:
                if old.requested_name != request.name: raise TenantException("denied")
                return TenantProvisioningResult(tenant_id=old.tenant_key,membership_id=old.member_key,created=False)
            key=fixed_tenant_id if fixed_tenant_id is not None else uuid4().hex
            if fixed_tenant_id is not None and (await session.scalar(select(Directory.id).where(Directory.tenant_key==key)) is not None or await session.scalar(select(Receipt.id).where(Receipt.tenant_key==key)) is not None):
                raise TenantException("denied")
            base=int(uuid4().hex[:12],16)
            await session.execute(insert(Directory).values(id=base,tenant_key=key,enabled=True))
            if self.fail_after_directory: raise RuntimeError("provisioning failure")
            member=uuid4().hex
            await session.execute(insert(Member).values(id=base+1,tenant_key=key,member_key=member,account=identity.account_id,department="d1",enabled=True))
            await session.execute(insert(Receipt).values(id=base+2,account=identity.account_id,request_key=request.idempotency_key,tenant_key=key,member_key=member,requested_name=request.name))
        return TenantProvisioningResult(tenant_id=key,membership_id=member,created=True)

@service(interface=DataPermissionProvider)
class DataRules(DataPermissionProvider):
    async def rules(self, identity): return (DataScopeRule(scope=DataScope.SELF),)
    async def descendants(self, identity, department_id): return frozenset()
    async def memberships(self, identity, department_ids): return frozenset()
    async def revision(self, identity): return identity.authorization_revision

@controller("/api/tenant-records", policy=RoutePolicy(realm=SecurityRealm.TENANT, permissions=("read",)))
class RecordController:
    def __init__(self, database: SessionProvider, tenant: TenantService):
        self.database, self.tenant = database, tenant
    @route("")
    async def records(self, target: str | None = None):
        if target is not None: self.tenant.require_target(target)
        async with self.database.read_session() as session:
            return (await session.scalars(select(Record.id).order_by(Record.id))).all()

@controller("/api/tenant-mode", policy=RoutePolicy.public())
@conditional(lambda config: config.get_config(TenantSettings).enabled)
class TenantModeController:
    @route("")
    async def mode(self): return dict(enabled=True)
"""


class TenantCase(SimpleNamespace):
    def issue(self, *, tenant="1", member="m1", **changes):
        token = OpaqueToken.generate()
        identity = LoginSession(
            application_id="dushan-ai-native",
            domain="admin",
            token_digest=OpaqueToken.digest(token),
            session_id=uuid4().hex,
            family_id=uuid4().hex,
            account_id="account-" + member,
            realm=SecurityRealm.TENANT,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision="1",
            scopes=frozenset(),
            tenant_id=tenant,
            membership_id=member,
            authority_tenant_id=tenant,
            authority_membership_id=member,
            dept_id="d1",
            access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
        ).model_copy(update=changes)
        self.tokens.sessions[identity.token_digest] = identity
        return token, identity

    @asynccontextmanager
    async def enter(self, token=None):
        if token is None:
            token, _ = self.issue()
        with self.app.state.application_context.execution():
            async with self.app.state.security.authorized(
                token, RoutePolicy(realm=SecurityRealm.TENANT, permissions=("read",))
            ):
                yield self


@pytest.fixture(params=TARGETS, ids=lambda target: target["name"])
def tenant_target(request):
    return request.param


@pytest.fixture
async def tenant_case(tenant_target, config_dir, module_package, tmp_path, request):
    options = getattr(request, "param", {})
    permissions = options.get("permissions", False)
    suffix = uuid4().hex[:12]
    package = "tenant_case_" + suffix
    source = SOURCE.format(
        suffix=suffix,
        public="@public_data(tenant_column=None)" if permissions else "",
        protected='@data_permission(permission_type="both", user_id_column="membership_id", dept_id_column="dept_id")'
        if permissions
        else "",
    )
    module_package(package, name=package, scan_roots=(".",), files={"models.py": source})
    module = importlib.import_module(package + ".models")
    url = tenant_target["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'tenant.sqlite').as_posix()}"
    sources = [dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)]
    database_values = {
        **ConfigFactory.values()["config"]["models"]["database"],
        "enabled": True,
        "sources": sources,
        "health_check_enabled": False,
    }
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.create_all)
            now = datetime.now(UTC).replace(tzinfo=None)
            audit = dict(create_time=now, update_time=now)
            if not options.get("empty", False):
                await connection.execute(
                    insert(module.Directory.__table__),
                    [
                        dict(id=1, tenant_key="1", enabled=True, **audit),
                        dict(id=2, tenant_key="2", enabled=True, **audit),
                    ],
                )
                await connection.execute(
                    insert(module.Member.__table__),
                    [
                        dict(
                            id=i,
                            tenant_key=t,
                            member_key=m,
                            account="account-" + m,
                            department="d1",
                            enabled=True,
                            **audit,
                        )
                        for i, t, m in ((1, "1", "m1"), (2, "1", "m2"), (3, "2", "m1"))
                    ],
                )
                await connection.execute(
                    insert(module.Record.__table__),
                    [
                        dict(
                            id=i,
                            tenant_id=t,
                            membership_id=m,
                            dept_id="d1",
                            name=n,
                            value=i,
                            **audit,
                        )
                        for i, t, m, n in (
                            (1, "1", "m1", "same"),
                            (2, "1", "m2", "other"),
                            (3, "2", "m1", "same"),
                        )
                    ],
                )
                await connection.execute(
                    insert(module.Child.__table__),
                    [
                        dict(
                            id=i,
                            tenant_id=t,
                            membership_id=m,
                            dept_id="d1",
                            parent_id=p,
                            name=f"child-{i}",
                            **audit,
                        )
                        for i, t, m, p in (
                            (101, "1", "m1", 1),
                            (102, "1", "m2", 1),
                            (103, "2", "m1", 3),
                        )
                    ],
                )
                await connection.execute(
                    insert(module.AccessApproval.__table__),
                    [
                        dict(
                            id=1,
                            kind="support",
                            actor="op1",
                            tenant_key="1",
                            reference="support-approved",
                            resource=module.Record.__table__.key,
                            enabled=True,
                            **audit,
                        ),
                        dict(
                            id=2,
                            kind="managed",
                            actor="1:m1",
                            tenant_key="2",
                            reference="g1:r1",
                            resource=module.Record.__table__.key,
                            enabled=True,
                            **audit,
                        ),
                    ],
                )
        values = {
            "banner": {"enabled": False},
            "modules": {"packages": ["framework", package], "enabled": ["framework", package]},
            "config": {
                "models": {
                    "database": database_values,
                    "security": {"enabled": True},
                    "tenant": {"enabled": options.get("enabled", True)},
                    "data_permission": {"enabled": permissions},
                    "cache": {
                        "enabled": options.get("cache", False),
                        "port": int(os.environ["DUSHAN_DP_REDIS_PORT"]),
                    },
                }
            },
        }
        if "profile" in options:
            values["config"]["models"]["tenant"]["profile"] = options["profile"]
        config_path = config_dir(values)
        app = create_app(base_dir=config_path, environ={})
        async with app.router.lifespan_context(app):
            case = TenantCase(
                app=app,
                tenant=app.state.tenant,
                database=app.state.database,
                module=module,
                engine=engine,
                options=options,
                config_path=config_path,
                config_values=values,
                package_path=tmp_path,
            )
            with app.state.application_context.execution():
                case.tokens = app.state.application_context.container.get(TokenProvider)
            yield case
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(module.metadata.drop_all)
        await engine.dispose()
