import importlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import create_async_engine

from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from server.starter_server import create_app

from .providers import metadata, permissions, sessions

ADAPTERS = """
from framework.starter_di.decorators.components import service
from framework.starter_security.spi.token_provider import TokenProvider
from framework.starter_security.spi.permission_provider import PermissionProvider
from framework.starter_security.bizlog.log_record_provider import LogRecordProvider
from starter_security.providers import SqlTokenProvider, SqlPermissionProvider, SqlLogRecordProvider

@service(interface=TokenProvider)
class Tokens(SqlTokenProvider): pass

@service(interface=PermissionProvider)
class Permissions(SqlPermissionProvider): pass

@service(interface=LogRecordProvider)
class Audit(SqlLogRecordProvider): pass
"""


class SecurityCase:
    def __init__(self, app, client):
        self.app, self.client = app, client
        self.service = app.state.security
        self.database = app.state.database
        self.application = app.state.application_context

    async def issue(self, *, granted=("read",), roles=("reader",), **changes):
        token = OpaqueToken.generate()
        state = dict(
            application_id=self.service.settings.application_id,
            domain=self.service.settings.default_domain,
            token_digest=OpaqueToken.digest(token),
            session_id=uuid4().hex,
            family_id=uuid4().hex,
            account_id="account-1",
            realm=SecurityRealm.ACCOUNT,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            revoked=False,
            account_enabled=True,
            credential_revision=1,
            current_credential_revision=1,
            authorization_revision="1",
            scopes=frozenset({"profile"}),
        )
        if changes.get("realm") is SecurityRealm.TENANT:
            state.update(
                access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
                membership_id="member-1",
                authority_tenant_id=changes["tenant_id"],
                authority_membership_id=changes.get("membership_id", "member-1"),
            )
        session = LoginSession(**{**state, **changes})
        with self.application.execution():
            async with self.database.transaction() as db:
                await db.execute(
                    insert(sessions).values(
                        digest=session.token_digest, data=session.model_dump(mode="json")
                    )
                )
                await self._permissions(db, session, granted, roles)
        return token, session

    async def _permissions(self, db, session, granted, roles):
        snapshot = PermissionSnapshot(
            binding=SecurityService.binding(session),
            revision=session.authorization_revision,
            permissions=frozenset(granted),
            roles=frozenset(roles),
        )
        await db.execute(
            insert(permissions).values(
                binding=snapshot.binding,
                revision=snapshot.revision,
                data=snapshot.model_dump(mode="json"),
            )
        )

    async def change(self, session, *, granted=None, roles=(), **changes):
        current = session.model_copy(update=changes)
        with self.application.execution():
            async with self.database.transaction() as db:
                await db.execute(
                    update(sessions)
                    .where(sessions.c.digest == session.token_digest)
                    .values(data=current.model_dump(mode="json"))
                )
                if granted is not None:
                    await self._permissions(db, current, granted, roles)
        return current

    async def get(self, token=None, path="/protected", **kwargs):
        headers = {} if token is None else {"Authorization": "Bearer " + token}
        headers.update(kwargs.pop("headers", {}))
        return await self.client.get(path, headers=headers, **kwargs)


@pytest.fixture
def security_module(module_package):
    name = "security_case_" + uuid4().hex
    module_package(name, name=name, scan_roots=(".",), files={"adapters.py": ADAPTERS})
    return name


@pytest.fixture
def security_factory(config_dir, tmp_path, security_module, module_package):
    @asynccontextmanager
    async def build(
        *,
        cache=False,
        audit=False,
        tenant=None,
        messages=None,
        workloads=None,
        policy=None,
        router=None,
        debug=False,
        database_url=None,
        **security,
    ):
        identifier = uuid4().hex
        url = (
            database_url
            if database_url is not None
            else f"sqlite+aiosqlite:///{(tmp_path / (identifier + '.sqlite')).as_posix()}"
        )
        schema = create_async_engine(url)
        async with schema.begin() as connection:
            await connection.run_sync(metadata.create_all)
        await schema.dispose()
        values = {
            "server": {"debug": debug},
            "expression": {"enabled": audit},
            "banner": {"enabled": False},
            "modules": {
                "packages": ["framework", security_module],
                "enabled": ["framework", security_module],
            },
            "config": {
                "models": {
                    "security": {
                        "enabled": True,
                        "application_id": "a" + identifier,
                        "permission_cache_enabled": cache,
                        "bizlog_enabled": audit,
                        **security,
                    },
                    "database": {
                        "enabled": True,
                        "health_check_enabled": False,
                        "slow_query_enabled": False,
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
        if cache:
            target = json.loads(os.environ.get("DUSHAN_SECURITY_TEST_REDIS", "null"))
            if target is None:
                pytest.skip("真实权限缓存验证需要本轮私有 Redis")
            values["config"]["models"]["cache"] = {
                "enabled": True,
                **target,
                "clients": [{"name": "default", "db": 0}],
            }
        if router is None:
            router = APIRouter()

            async def who():
                session = app.state.security.context.require()
                return {"account": session.account_id, "tenant": session.tenant_id}

            router.add_api_route("/protected", (policy or RoutePolicy(("read",)))(who))
            router.add_api_route("/public", RoutePolicy.public()(lambda: {"public": True}))
        optional = "security_optional_" + identifier
        source = "from framework.starter_di.decorators.components import service\n"
        for name, interface, package, methods, instance in (
            (
                "tenant",
                "TenantAccessProvider",
                "tenant_access_provider",
                ("supports", "enter", "enter_workload"),
                tenant,
            ),
            (
                "messages",
                "MessageSecurityProvider",
                "message_security_provider",
                ("issue", "verify", "issue_workload", "verify_workload"),
                messages,
            ),
            ("workloads", "WorkloadProvider", "workload_provider", ("authenticate",), workloads),
        ):
            if instance is None:
                continue
            source += f"from framework.starter_security.spi.{package} import {interface}\n"
            source += f"@service(interface={interface})\nclass Bound{interface}({interface}):\n    def __init__(self):\n        self.delegate = {name}\n"
            for method in methods:
                keyword = "" if name == "tenant" else "async "
                awaiting = "" if name == "tenant" else "await "
                source += f"    {keyword}def {method}(self, *args, **kwargs):\n        return {awaiting}self.delegate.{method}(*args, **kwargs)\n"
        module_package(optional, files={"adapters.py": source})
        optional_module = importlib.import_module(optional + ".adapters")
        optional_module.tenant, optional_module.messages, optional_module.workloads = (
            tenant,
            messages,
            workloads,
        )
        values["modules"]["packages"].append(optional)
        values["modules"]["enabled"].append(optional)
        from fixtures.starter_steps import StarterSteps

        app = create_app(
            steps=StarterSteps.without_tenant(),
            base_dir=config_dir(values),
            environ={},
            routers=(RouterRegistration(router),),
            access_provider=SecurityAccess(),
        )
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app, raise_app_exceptions=False), base_url="https://test"
            ) as client:
                case = SecurityCase(app, client)
                try:
                    yield case
                finally:
                    if cache:
                        redis = app.state.cache.get_client("default")
                        keys = [
                            key
                            async for key in redis.scan_iter(
                                match=f"security:permissions:{case.service.settings.application_id}:*"
                            )
                        ]
                        if keys:
                            await redis.delete(*keys)
            if audit:
                with case.application.execution():
                    assert (
                        case.application.get_bean(BizLogService).resources()["active_operations"]
                        == 0
                    )
        assert case.service.resources() == {"state": "closed", "active_operations": 0}
        assert app.state.application_context is None and app.state.database is None

    return build
