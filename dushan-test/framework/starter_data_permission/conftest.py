import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import mapped_column, relationship

from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from fixtures.starter_steps import StarterSteps
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_data_permission.enums.data_scope import DataScope
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_web.routing.route_policy import RoutePolicy
from server.starter_server import create_app


class Tokens:
    def __init__(self):
        self.sessions = {}

    async def resolve(self, digest, **kwargs):
        return self.sessions.get(digest)


class Permissions:
    async def snapshot(self, identity, *, binding):
        return PermissionSnapshot(
            binding=binding,
            revision=identity.authorization_revision,
            permissions=frozenset({"read", "write"}),
            roles=frozenset({"reader"}),
        )


class TenantBoundary:
    """只验证 Security 的正式准入调用，不能计作生产 Tenant 实现。"""

    def __init__(self):
        self.active = 0

    def supports(self, capability):
        return capability == "direct_membership"

    @asynccontextmanager
    async def enter(self, identity, policy):
        if identity.tenant_id not in {"t1", "t2", "t3"}:
            raise SecurityException("denied")
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1

    @asynccontextmanager
    async def enter_workload(self, identity, capability):
        if identity.tenant_id not in {"t1", "t2", "t3"}:
            raise SecurityException("denied")
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1


class SqlRules:
    def __init__(self, database, rules, members, revisions):
        self.database, self.table, self.members = database, rules, members
        self.revisions = revisions
        self.calls = {"rules": 0, "descendants": 0, "memberships": 0, "revision": 0}
        self.failure = None
        self.wait = None

    async def rules(self, identity):
        self.calls["rules"] += 1
        if self.failure is not None:
            raise self.failure
        if self.wait is not None:
            await self.wait.wait()
        async with self.database.read_session(force_primary=True) as session:
            rows = (
                (
                    await session.execute(
                        select(self.table).where(
                            self.table.c.tenant == identity.tenant_id,
                            self.table.c.member == identity.membership_id,
                        )
                    )
                )
                .mappings()
                .all()
            )
        return tuple(
            DataScopeRule(
                scope=DataScope.from_code(row["scope"]),
                department_ids=frozenset(row["departments"]),
            )
            for row in rows
        )

    async def descendants(self, identity, department_id):
        self.calls["descendants"] += 1
        descendants = (
            select(self.members.c.department)
            .where(
                self.members.c.tenant == identity.tenant_id,
                self.members.c.parent == department_id,
            )
            .cte("permission_descendants", recursive=True)
        )
        descendants = descendants.union(
            select(self.members.c.department)
            .join(descendants, self.members.c.parent == descendants.c.department)
            .where(self.members.c.tenant == identity.tenant_id)
        )
        async with self.database.read_session(force_primary=True) as session:
            return frozenset((await session.scalars(select(descendants.c.department))).all())

    async def memberships(self, identity, department_ids):
        self.calls["memberships"] += 1
        async with self.database.read_session(force_primary=True) as session:
            return frozenset(
                (
                    await session.scalars(
                        select(self.members.c.member).where(
                            self.members.c.tenant == identity.tenant_id,
                            self.members.c.department.in_(department_ids),
                        )
                    )
                ).all()
            )

    async def revision(self, identity):
        self.calls["revision"] += 1
        async with self.database.read_session(force_primary=True) as session:
            return await session.scalar(
                select(self.revisions.c.revision).where(
                    self.revisions.c.tenant == identity.tenant_id,
                    self.revisions.c.member == identity.membership_id,
                )
            )


class PermissionCase:
    def issue(self, *, tenant="t1", member="m1", department="d1", **changes):
        token = OpaqueToken.generate()
        identity = LoginSession(
            application_id=self.security.settings.application_id,
            domain="admin",
            token_digest=OpaqueToken.digest(token),
            session_id=uuid4().hex,
            family_id=uuid4().hex,
            account_id="account-" + member,
            realm=SecurityRealm.TENANT,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision=self.revisions.get((tenant, member), "1"),
            scopes=frozenset(),
            tenant_id=tenant,
            membership_id=member,
            authority_tenant_id=tenant,
            authority_membership_id=member,
            dept_id=department,
            access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
        ).model_copy(update=changes)
        self.tokens.sessions[identity.token_digest] = identity
        return token, identity

    @asynccontextmanager
    async def enter(self, token=None):
        if token is None:
            token, _ = self.issue()
        with self.application.execution():
            async with self.security.authorized(token, self.route):
                yield self

    async def set_rules(self, *scopes, tenant="t1", member="m1", custom=()):
        key = (tenant, member)
        previous = self.revisions.get(key)
        revision = str(int(previous or "0") + 1)
        with self.application.execution():
            async with self.database.transaction() as session:
                await session.execute(
                    delete(self.rules).where(
                        self.rules.c.tenant == tenant, self.rules.c.member == member
                    )
                )
                if scopes:
                    await session.execute(
                        insert(self.rules),
                        [
                            dict(
                                id=uuid4().hex,
                                tenant=tenant,
                                member=member,
                                scope=scope.code,
                                departments=list(custom) if scope is DataScope.DEPT_CUSTOM else [],
                            )
                            for scope in scopes
                        ],
                    )
                if previous is None:
                    await session.execute(
                        insert(self.provider.revisions).values(
                            tenant=tenant, member=member, revision=revision
                        )
                    )
                else:
                    await session.execute(
                        update(self.provider.revisions)
                        .where(
                            self.provider.revisions.c.tenant == tenant,
                            self.provider.revisions.c.member == member,
                        )
                        .values(revision=revision)
                    )
        self.revisions[key] = revision
        for digest, identity in tuple(self.tokens.sessions.items()):
            if (identity.tenant_id, identity.membership_id) == key:
                self.tokens.sessions[digest] = identity.model_copy(
                    update={"authorization_revision": revision}
                )

    async def ids(self, statement=None):
        async with self.database.read_session() as session:
            return sorted(
                (
                    await session.scalars(select(self.Item.id) if statement is None else statement)
                ).all()
            )


@pytest.fixture(params=TARGETS, ids=lambda target: target["name"])
def permission_target(request):
    return request.param


@pytest.fixture
async def permission_case(permission_target, config_dir, tmp_path, request):
    suffix = uuid4().hex[:12]
    options = getattr(request, "param", {})
    model_scope = options.get("model_scope", "both")
    member_attribute = "owner" if options.get("renamed") else "membership_id"
    metadata = MetaData()
    item_table, child_table = "dp_item_" + suffix, "dp_child_" + suffix
    Item = type(
        "Item_" + suffix,
        (BaseDO,),
        {
            "__tablename__": item_table,
            "metadata": metadata,
            "__table_args__": (UniqueConstraint("tenant_id", "name"),),
            "tenant_id": mapped_column(String(64), nullable=False),
            member_attribute: mapped_column("membership_id", String(64), nullable=True),
            "dept_id": mapped_column(String(64), nullable=True),
            "name": mapped_column(String(64), nullable=False),
            "value": mapped_column(Integer, nullable=False),
        },
    )
    Child = type(
        "Child_" + suffix,
        (BaseDO,),
        {
            "__tablename__": child_table,
            "metadata": metadata,
            "tenant_id": mapped_column(String(64), nullable=False),
            "membership_id": mapped_column(String(64), nullable=True),
            "dept_id": mapped_column(String(64), nullable=True),
            "item_id": mapped_column(
                ForeignKey(item_table + ".id", ondelete="CASCADE"), nullable=False
            ),
            "name": mapped_column(String(64), nullable=False),
        },
    )
    Item.children = relationship(Child, lazy="selectin")
    Item = data_permission(
        permission_type={"department": "dept_scope", "membership": "user_scope", "both": "both"}[
            model_scope
        ],
        user_id_column=None if model_scope == "department" else "membership_id",
        dept_id_column=None if model_scope == "membership" else "dept_id",
    )(Item)
    Child = data_permission(
        permission_type="both", user_id_column="membership_id", dept_id_column="dept_id"
    )(Child)
    rules = Table(
        "dp_rules_" + suffix,
        metadata,
        Column("id", String(32), primary_key=True),
        Column("tenant", String(64)),
        Column("member", String(64)),
        Column("scope", Integer),
        Column("departments", JSON),
    )
    members = Table(
        "dp_members_" + suffix,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tenant", String(64)),
        Column("member", String(64)),
        Column("department", String(64)),
        Column("parent", String(64), nullable=True),
    )
    revisions = Table(
        "dp_revision_" + suffix,
        metadata,
        Column("tenant", String(64), primary_key=True),
        Column("member", String(64), primary_key=True),
        Column("revision", String(64)),
    )
    url = permission_target["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'dp.sqlite').as_posix()}"
    source = dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)
    caching = getattr(request, "param", {}).get("cache", False)
    if caching and "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("需要本轮独立 Redis")
    cache_values = (
        {"enabled": True, "host": "127.0.0.1", "port": int(os.environ["DUSHAN_DP_REDIS_PORT"])}
        if caching
        else {"enabled": False}
    )
    app = create_app(
        steps=StarterSteps.without_tenant(),
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "config": {
                    "models": {
                        "cache": cache_values,
                        "database": {
                            "enabled": True,
                            "health_check_enabled": False,
                            "slow_query_enabled": False,
                            "sources": [source],
                        },
                    }
                },
            }
        ),
        environ={},
    )
    schema = create_async_engine(url)
    created = False
    try:
        async with schema.begin() as connection:
            await connection.run_sync(metadata.create_all)
            created = True
            await connection.execute(
                insert(Item.__table__),
                [
                    dict(
                        id=i,
                        tenant_id=t,
                        membership_id=m,
                        dept_id=d,
                        name=f"row-{i}",
                        value=i,
                        create_time=datetime.now(UTC).replace(tzinfo=None),
                        update_time=datetime.now(UTC).replace(tzinfo=None),
                    )
                    for i, t, m, d in (
                        (1, "t1", "m1", "d1"),
                        (2, "t1", "m2", "d1"),
                        (3, "t1", "m3", "d2"),
                        (4, "t1", "m4", "d3"),
                        (5, "t2", "m1", "d1"),
                        (6, "t2", "m2", "d2"),
                        (7, "t3", "m1", "d1"),
                    )
                ],
            )
            await connection.execute(
                insert(Child.__table__),
                [
                    dict(
                        id=i,
                        item_id=p,
                        tenant_id=t,
                        membership_id=m,
                        dept_id=d,
                        name=f"child-{i}",
                        create_time=datetime.now(UTC).replace(tzinfo=None),
                        update_time=datetime.now(UTC).replace(tzinfo=None),
                    )
                    for i, p, t, m, d in (
                        (101, 1, "t1", "m1", "d1"),
                        (102, 1, "t1", "m3", "d2"),
                        (103, 3, "t1", "m1", "d1"),
                    )
                ],
            )
            await connection.execute(
                insert(members),
                [
                    dict(id=i, tenant=t, member=m, department=d, parent=p)
                    for i, t, m, d, p in (
                        (1, "t1", "m1", "d1", None),
                        (2, "t1", "m2", "d1", None),
                        (3, "t1", "m3", "d2", "d1"),
                        (4, "t1", "m4", "d3", "d2"),
                        (5, "t2", "m1", "d1", None),
                        (6, "t2", "m2", "d2", "d1"),
                    )
                ],
            )
        async with app.router.lifespan_context(app):
            case = PermissionCase()
            case.app, case.application, case.database = (
                app,
                app.state.application_context,
                app.state.database,
            )
            case.Item, case.Child, case.rules, case.members, case.schema = (
                Item,
                Child,
                rules,
                members,
                schema,
            )
            case.route = RoutePolicy(realm=SecurityRealm.TENANT, permissions=("read",))
            case.tokens, case.tenant = Tokens(), TenantBoundary()
            case.revisions = {}
            case.provider = SqlRules(case.database, rules, members, revisions)
            with case.application.execution():
                case.context = case.application.container.get(SecurityContext)
                cache = case.application.container.get(CacheHandler)
            case.service = DataPermissionService(
                DataPermissionSettings.model_validate(
                    {
                        **ConfigFactory.values()["config"]["models"]["data_permission"],
                        "enabled": True,
                        "cache_enabled": caching,
                    }
                ),
                case.context,
                case.provider,
                cache,
            )
            case.security = SecurityService(
                SecuritySettings.model_validate(
                    {
                        **ConfigFactory.values()["config"]["models"]["security"],
                        "enabled": True,
                    }
                ),
                case.tokens,
                Permissions(),
                cache,
                case.context,
            )
            case.registry = DataPermissionRegistry(
                [
                    Item,
                    Child,
                    DataPermissionModel(rules, True, None),
                    DataPermissionModel(members, True, None),
                    DataPermissionModel(revisions, True, None),
                ]
            )
            case.policy = DataPermissionPolicy(case.registry, case.service)
            case.mapper = BaseMapper(Item)
            case.mapper.session_provider = case.database
            await case.security.open(tenant=case.tenant, data_access=case.service)
            with case.database.use_session_policy(case.policy):
                try:
                    await case.set_rules(DataScope.SELF)
                    yield case
                finally:
                    await case.security.close()
                    await case.service.close()
    finally:
        try:
            if created:
                async with schema.begin() as connection:
                    await connection.run_sync(metadata.drop_all)
        finally:
            await schema.dispose()
