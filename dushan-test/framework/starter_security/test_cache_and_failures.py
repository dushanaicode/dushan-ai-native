import pytest
from fastapi import APIRouter

from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from server.starter_server import create_app


async def test_real_cache_versions_disable_and_invalidate(security_factory):
    async with security_factory(cache=True) as case:
        token, session = await case.issue()
        for _ in range(3):
            assert (await case.get(token)).json()["account"] == "account-1"
        assert case.service.tokens.reads == 3
        assert case.service.permissions.reads == 1
        with case.application.execution():
            await case.service.invalidate_permissions(session)
        assert (await case.get(token)).json()["account"] == "account-1"
        assert case.service.permissions.reads == 2
        changed = await case.change(session, authorization_revision="2", granted=())
        assert (await case.get(token)).json()["code"] == SecurityErrorCodes.DENIED.code
        await case.change(changed, account_enabled=False)
        assert (await case.get(token)).json()["code"] == SecurityErrorCodes.DISABLED.code


async def test_real_cache_never_hides_revocation_or_credentials_change(security_factory):
    async with security_factory(cache=True) as case:
        for change, expected in (
            ({"revoked": True}, SecurityErrorCodes.REVOKED.code),
            ({"current_credential_revision": 2}, SecurityErrorCodes.CREDENTIALS.code),
        ):
            token, session = await case.issue()
            assert (await case.get(token)).json()["account"] == "account-1"
            await case.change(session, **change)
            assert (await case.get(token)).json()["code"] == expected


@pytest.mark.parametrize("dependency", ["tokens", "permissions", "cache", "database"])
async def test_dependency_failures_never_allow(security_factory, monkeypatch, dependency):
    async with security_factory(cache=dependency == "cache") as case:
        token, _ = await case.issue()

        async def unavailable(*args, **kwargs):
            raise RuntimeError("private-provider-value password=private-password")

        if dependency == "tokens":
            monkeypatch.setattr(case.service.tokens, "resolve", unavailable)
        elif dependency == "permissions":
            monkeypatch.setattr(case.service.permissions, "snapshot", unavailable)
        elif dependency == "cache":
            monkeypatch.setattr(case.service.cache, "get_or_load", unavailable)
        else:
            await case.database.close()
        response = await case.get(token)
        assert (
            response.status_code == 200
            and response.json()["code"] == SecurityErrorCodes.UNAVAILABLE.code
        )
        assert "private" not in response.text
        assert case.service.context.current() is None


async def test_missing_provider_startup_fails(config_dir):
    app = create_app(
        base_dir=config_dir({"config": {"models": {"security": {"enabled": True}}}}), environ={}
    )
    with pytest.raises(Exception) as failure:
        async with app.router.lifespan_context(app):
            pytest.fail("缺少正式身份提供者不能启动")
    assert "TokenProvider" in str(failure.value) or "TokenProvider" in str(failure.value.__cause__)
    assert app.state.application_context is None and app.state.security is None


async def test_security_disabled_protected_route_not_public(config_dir):
    router = APIRouter()
    router.add_api_route("/protected", RoutePolicy()(lambda: {"leak": True}))
    app = create_app(
        base_dir=config_dir(),
        environ={},
        access_provider=SecurityAccess(),
        routers=(RouterRegistration(router),),
    )
    from httpx import ASGITransport, AsyncClient

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            response = await client.get("/protected")
            assert (
                response.json()["code"] == SecurityErrorCodes.CONFIGURATION.code
                and "leak" not in response.text
            )


@pytest.mark.parametrize(
    "values",
    [
        {"requires_identity": False, "roles": ("admin",)},
        {"requires_identity": False, "scopes": ("read",)},
        {"permissions": ("read", "read")},
        {"permission_mode": "guess"},
    ],
)
def test_conflicting_policy_is_rejected(values):
    with pytest.raises((ValueError, TypeError)):
        RoutePolicy(**values)


def test_conflicting_public_declaration():
    def endpoint():
        pass

    RoutePolicy()(endpoint)
    with pytest.raises(ValueError, match="冲突"):
        RoutePolicy.public()(endpoint)


async def test_bizlog_requires_existing_expression_capability(config_dir, security_module):
    app = create_app(
        base_dir=config_dir(
            {
                "modules": {
                    "packages": ["framework", security_module],
                    "enabled": ["framework", security_module],
                },
                "config": {"models": {"security": {"enabled": True, "bizlog_enabled": True}}},
                "expression": {"enabled": False},
            }
        ),
        environ={},
    )
    with pytest.raises(Exception):
        async with app.router.lifespan_context(app):
            pytest.fail("不完整的审计配置不能就绪")
    assert app.state.security is None and app.state.application_context is None


async def test_missing_permission_provider_fails_startup(config_dir, module_package):
    from .conftest import ADAPTERS

    source = ADAPTERS.replace("@service(interface=PermissionProvider)", "")
    module_package("security_without_permissions", files={"adapters.py": source})
    app = create_app(
        base_dir=config_dir(
            {
                "modules": {
                    "packages": ["framework", "security_without_permissions"],
                    "enabled": ["framework", "security_without_permissions"],
                },
                "config": {"models": {"security": {"enabled": True}}},
            }
        ),
        environ={},
    )
    with pytest.raises(Exception) as error:
        async with app.router.lifespan_context(app):
            pytest.fail("权限适配缺失不能就绪")
    assert "PermissionProvider" in str(error.value) or "PermissionProvider" in str(
        error.value.__cause__
    )
    assert app.state.application_context is None


async def test_provider_revision_mismatch_is_infrastructure_failure(security_factory, monkeypatch):
    async with security_factory() as case:
        token, session = await case.issue()
        original = case.service.permissions.snapshot

        async def wrong_version(*args, **kwargs):
            value = await original(*args, **kwargs)
            return value.model_copy(update={"revision": "old"})

        monkeypatch.setattr(case.service.permissions, "snapshot", wrong_version)
        assert (await case.get(token)).json()["code"] == SecurityErrorCodes.UNAVAILABLE.code
        with case.application.execution():
            with pytest.raises(SecurityException):
                await case.service.invalidate_permissions(
                    session.model_copy(update={"application_id": "other"})
                )
