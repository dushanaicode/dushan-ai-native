import importlib
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import APIRouter, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.starter_steps import StarterSteps
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from server.starter_server import create_app

SOURCE = """
from contextlib import asynccontextmanager
from sqlalchemy import MetaData, String
from sqlalchemy.orm import mapped_column
from framework.starter_database.model.base_do import BaseDO
from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_data_permission.spi.data_permission_provider import DataPermissionProvider
from framework.starter_di.decorators.components import service
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider

@data_permission(permission_type="user_scope", user_id_column="membership_id")
class Record(BaseDO):
    __tablename__ = "{table_name}"
    metadata = MetaData()
    tenant_id = mapped_column(String(64), nullable=False)
    membership_id = mapped_column(String(64), nullable=False)

@service(interface=TokenProvider)
class Tokens(TokenProvider):
    def __init__(self): self.sessions = dict()
    async def resolve(self, digest, **kwargs): return self.sessions.get(digest)

@service(interface=PermissionProvider)
class Permissions(PermissionProvider):
    async def snapshot(self, identity, *, binding):
        return PermissionSnapshot(binding=binding, revision=identity.authorization_revision,
            permissions=frozenset(("read",)), roles=frozenset())

@service(interface=DataPermissionProvider)
class DataRules(DataPermissionProvider):
    async def rules(self, identity): return (DataScopeRule(scope=DataScope.SELF),)
    async def descendants(self, identity, department_id): return frozenset()
    async def memberships(self, identity, department_ids): return frozenset()
    async def revision(self, identity): return identity.authorization_revision

@service(interface=TenantAccessProvider)
class Tenant(TenantAccessProvider):
    def supports(self, capability): return False
    @asynccontextmanager
    async def enter(self, identity, policy):
        assert identity.tenant_id == "t1"
        yield
"""


@pytest.mark.parametrize("cached", [False, True])
async def test_scanner_di_http_and_resource_close(config_dir, module_package, tmp_path, cached):
    if cached and "DUSHAN_DP_REDIS_PORT" not in os.environ:
        pytest.skip("完整缓存装配需要本轮私有 Redis")
    name = "dp_assembly_" + uuid4().hex
    module_package(
        name, name=name, scan_roots=(".",), files={"adapters.py": SOURCE.format(table_name=name)}
    )
    module = importlib.import_module(name + ".adapters")
    table = module.Record.__table__
    url = f"sqlite+aiosqlite:///{(tmp_path / 'assembly.sqlite').as_posix()}"
    schema = create_async_engine(url)
    async with schema.begin() as connection:
        await connection.run_sync(table.create)
        now = datetime.now(UTC).replace(tzinfo=None)
        await connection.execute(
            insert(table),
            [
                dict(id=i, tenant_id=t, membership_id=m, create_time=now, update_time=now)
                for i, t, m in ((1, "t1", "m1"), (2, "t1", "m2"), (3, "t2", "m1"))
            ],
        )
    router = APIRouter()

    @router.get("/records")
    async def records(request: Request):
        async with request.app.state.database.read_session() as session:
            return (await session.scalars(select(module.Record.id))).all()

    app = create_app(
        steps=StarterSteps.without_tenant(),
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {"packages": ["framework", name], "enabled": ["framework", name]},
                "config": {
                    "models": {
                        "data_permission": {"enabled": True, "cache_enabled": cached},
                        "cache": {
                            "enabled": cached,
                            "port": int(os.environ["DUSHAN_DP_REDIS_PORT"]) if cached else 6379,
                        },
                        "security": {"enabled": True},
                        "database": {
                            "enabled": True,
                            "health_check_enabled": False,
                            "sources": [
                                dict(
                                    name="primary",
                                    url=url,
                                    role="primary",
                                    weight=100,
                                    pool=None,
                                    tls=None,
                                )
                            ],
                        },
                    }
                },
            }
        ),
        environ={},
        access_provider=SecurityAccess(),
        routers=(
            RouterRegistration(
                router, policy=RoutePolicy(realm=SecurityRealm.TENANT, permissions=("read",))
            ),
        ),
    )
    try:
        async with app.router.lifespan_context(app):
            application = app.state.application_context
            with application.execution():
                service = application.container.get(DataPermissionService)
                assert app.state.security._data_access is service
                tokens = application.container.get(TokenProvider)
                token = OpaqueToken.generate()
                identity = LoginSession(
                    application_id="dushan-ai-native",
                    domain="admin",
                    token_digest=OpaqueToken.digest(token),
                    session_id=uuid4().hex,
                    family_id=uuid4().hex,
                    account_id="a1",
                    realm=SecurityRealm.TENANT,
                    expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    revoked=False,
                    account_enabled=True,
                    credential_revision=1,
                    current_credential_revision=1,
                    authorization_revision="1",
                    scopes=frozenset(),
                    tenant_id="t1",
                    membership_id="m1",
                    authority_tenant_id="t1",
                    authority_membership_id="m1",
                    access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
                )
                tokens.sessions[identity.token_digest] = identity
            async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
                response = await client.get(
                    "/records", headers={"Authorization": "Bearer " + token}
                )
                assert response.status_code == 200
                assert response.json() == [1]
                response = await client.get("/records")
                assert response.json().get("code") == SecurityErrorCodes.MISSING.code
            assert service._active == 0
        assert service._closed and service._active == 0
        assert app.state.database is None and app.state.security is None
    finally:
        async with schema.begin() as connection:
            await connection.run_sync(table.drop)
        await schema.dispose()
