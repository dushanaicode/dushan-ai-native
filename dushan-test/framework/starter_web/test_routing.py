import importlib
import inspect

import pytest
from fastapi import APIRouter, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from fastapi.testclient import TestClient

from framework.common.security.request_identity import RequestIdentity
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.authenticated_websocket_route import AuthenticatedWebSocketRoute
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app

pytestmark = pytest.mark.unit

CONTROLLER = """
from __future__ import annotations
from typing import Annotated
from uuid import uuid4
from fastapi import Depends, Query, Header, Request
from framework.starter_web.response.result import Result
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.context.request_context import RequestContext

@service
class Greeting:
    def __init__(self):
        self.id = uuid4().hex

class Payload(BaseRequestVO):
    display_name: str

@controller('/declared', tags=('declared',), policy=RoutePolicy.public())
class Endpoints:
    greeting: Greeting = Inject()

    @route('/{number}', response_model=Result[dict])
    def read(self, number: int, q: Annotated[list[int], Query()], request: Request,
             marker: Annotated[str, Header()] = 'default',
             greeting: Greeting = Depends(DiDependency(Greeting))):
        return Result.success({'number': number, 'q': q, 'marker': marker,
                               'same': greeting is self.greeting, 'id': greeting.id,
                               'context': RequestContext.current().connection.app is request.app})

    @route('/write', methods=('POST',), response_model=Result[str])
    async def write(self, payload: Payload):
        return Result.success(payload.display_name)

@controller('/transient', scope=ComponentScopeEnum.TRANSIENT, policy=RoutePolicy.public())
class Transient:
    def __init__(self):
        self.id = uuid4().hex
    @route('')
    async def read(self):
        return {'id': self.id}
"""


def feature_app(
    module_package, config_dir, *, source=CONTROLLER, scanner=True, enabled=True, **kwargs
):
    module_package(
        "web_feature",
        files={"controllers.py": source},
        definitions=("controllers:Endpoints", "controllers:Greeting", "controllers:Transient")
        if not scanner
        else (),
    )
    root = config_dir(
        {
            "modules": {
                "packages": ["framework", "web_feature"],
                "enabled": ["framework", "web_feature"] if enabled else ["framework"],
            },
            "scanner": {"enabled": scanner},
        }
    )
    return create_app(base_dir=root, environ={}, **kwargs)


@pytest.mark.parametrize("scanner", [True, False])
def test_discovery_explicit_di_parameters_and_cleanup(module_package, config_dir, scanner):
    app = feature_app(module_package, config_dir, scanner=scanner)
    definitions = importlib.import_module("web_feature.controllers")
    signature = inspect.signature(definitions.Endpoints.read)
    with TestClient(app) as client:
        runtime = app.state.application_context
        response = client.get("/declared/7?q=1&q=2", headers={"marker": "ok"})
        assert response.status_code == 200
        assert response.json()["data"] | {"id": ""} == {
            "number": 7,
            "q": [1, 2],
            "marker": "ok",
            "same": True,
            "context": True,
            "id": "",
        }
        assert (
            client.post("/declared/write", json={"displayName": "hello"}).json()["data"] == "hello"
        )
        invalid = client.get("/declared/wrong?q=secret")
        assert invalid.status_code == 200 and invalid.json()["code"] == 422
        assert "secret" not in invalid.text
        assert client.get("/transient").json()["id"] != client.get("/transient").json()["id"]
        assert runtime.get_statistics()["executions"] == 0
        document = client.get("/openapi.json").json()
        operation = document["paths"]["/declared/{number}"]["get"]
        assert {p["name"] for p in operation["parameters"]} == {"number", "q", "marker"}
        assert "422" not in operation["responses"]
        assert document["paths"]["/declared/write"]["post"]["requestBody"]["content"][
            "application/json"
        ]
    assert inspect.signature(definitions.Endpoints.read) == signature
    assert "/declared/{number}" not in app.openapi()["paths"]
    assert runtime.get_statistics()["executions"] == 0


def test_modules_off_and_multiple_applications(module_package, config_dir):
    first = feature_app(module_package, config_dir)
    second = create_app(base_dir=first.state.bootstrap.base_dir, environ={})
    disabled = create_app(
        base_dir=first.state.bootstrap.base_dir, environ={"MODULES_ENABLED": '["framework"]'}
    )
    with TestClient(first) as a, TestClient(second) as b, TestClient(disabled) as c:
        one = a.get("/declared/1?q=1").json()["data"]["id"]
        assert one == a.get("/declared/1?q=2").json()["data"]["id"]
        assert one != b.get("/declared/1?q=1").json()["data"]["id"]
        assert c.get("/declared/1?q=1").json()["code"] == 404
        assert "/declared/{number}" not in c.get("/openapi.json").json()["paths"]


def test_conditional_controller_is_not_published(module_package, config_dir):
    source = CONTROLLER.replace(
        "@controller('/declared'", "@conditional(lambda config: False)\n@controller('/declared'"
    )
    source = source.replace(
        "from typing import Annotated",
        "from typing import Annotated\nfrom framework.starter_di.decorators.conditional import conditional",
    )
    app = feature_app(module_package, config_dir, source=source)
    with TestClient(app) as client:
        assert client.get("/declared/1?q=1").json()["code"] == 404
        assert client.get("/transient").status_code == 200


@pytest.mark.parametrize("first,second", [("/same", "/same"), ("/items/{id}", "/items/{name}")])
def test_explicit_duplicates_fail_before_mutation(config_dir, first, second):
    router = APIRouter()
    router.add_api_route(first, lambda: {})
    app = create_app(
        base_dir=config_dir(),
        environ={},
        routers=[RouterRegistration(router, policy=RoutePolicy.public())],
    )
    previous = tuple(app.routes)
    other = APIRouter()
    other.add_api_route(second, lambda: {})
    with pytest.raises(ValueError, match="重复路由"):
        app.state.web_routes.include(RouterRegistration(other))
    assert tuple(app.routes) == previous


def test_native_late_registration_is_audited_at_startup(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    app.add_api_route("/health", lambda: {})
    with pytest.raises(BootstrapError) as error, TestClient(app):
        pass
    assert "重复路由" in str(error.value.__cause__)
    assert app.state.bootstrap.definitions is None


def test_explicit_router_keeps_lifespan(config_dir):
    from contextlib import asynccontextmanager

    events = []

    @asynccontextmanager
    async def lifespan(app):
        events.append("open")
        yield
        events.append("close")

    router = APIRouter(lifespan=lifespan)
    router.add_api_route("/native", lambda: {"ok": True})
    app = create_app(
        base_dir=config_dir(),
        environ={},
        routers=[RouterRegistration(router, "/api", RoutePolicy.public())],
    )
    with TestClient(app) as client:
        assert client.get("/api/native").json() == {"ok": True}
    assert events == ["open", "close"]


def test_protected_registration_requires_provider(config_dir):
    router = APIRouter()
    router.add_api_route("/protected", lambda: {})
    with pytest.raises(ValueError, match="缺少授权提供者"):
        create_app(
            base_dir=config_dir(),
            environ={},
            routers=[RouterRegistration(router, policy=RoutePolicy())],
        )


def test_security_dependency_openapi_and_tenant_boundary(config_dir):
    bearer = HTTPBearer(auto_error=False)

    async def provider(
        scopes: SecurityScopes,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    ):
        assert scopes.scopes == ["read"]
        if credentials is None:
            return None
        # 仅验证接点：测试令牌决定身份，不能用于生产认证。
        if credentials.credentials == "denied":
            from fastapi import HTTPException

            raise HTTPException(403)
        return RequestIdentity(
            principal_id="alice",
            tenant_id="tenant-a" if credentials.credentials == "tenant" else None,
        )

    router = APIRouter()

    @router.get("/protected")
    async def protected():
        return RequestContext.current().identity

    app = create_app(
        base_dir=config_dir(),
        environ={},
        access_provider=provider,
        routers=[RouterRegistration(router, policy=RoutePolicy(("read",), tenant_required=True))],
    )
    with TestClient(app) as client:
        missing = client.get("/protected")
        assert missing.status_code == 200 and missing.json()["code"] == 401
        assert missing.headers["www-authenticate"] == "Bearer"
        for token, code in (
            ("denied", 403),
            ("no-tenant", SecurityErrorCodes.DENIED.code),
        ):
            assert (
                client.get("/protected", headers={"Authorization": f"Bearer {token}"}).json()[
                    "code"
                ]
                == code
            )
        response = client.get("/protected", headers={"Authorization": "Bearer tenant"})
        assert response.json() == {"principal_id": "alice", "tenant_id": "tenant-a"}
        document = client.get("/openapi.json").json()
        assert document["paths"]["/protected"]["get"]["security"] == [{"HTTPBearer": ["read"]}]
        assert document["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    with pytest.raises(RuntimeError, match="有效"):
        RequestContext.current()


def test_decorators_leave_functions_and_annotations_intact():
    async def method(self, number: int) -> str:
        return str(number)

    before = inspect.signature(method)
    assert route("/n")(method) is method
    assert inspect.signature(method) == before

    @controller("/test")
    class Controller:
        pass

    with pytest.raises(ValueError, match="重复声明"):
        controller("/other")(Controller)


def test_ignored_protected_declaration_is_not_published(config_dir):
    router = APIRouter()

    @router.get("/unsafe")
    @route("/unsafe", policy=RoutePolicy())
    async def unsafe():
        return {}

    with pytest.raises(ValueError, match="裸端点"):
        create_app(base_dir=config_dir(), environ={}, routers=[RouterRegistration(router)])


def test_controller_with_policy_fails_without_provider(module_package, config_dir):
    source = CONTROLLER.replace("@route('/{number}',", "@route('/{number}', policy=RoutePolicy(),")
    app = feature_app(module_package, config_dir, source=source)
    with pytest.raises(BootstrapError) as error, TestClient(app):
        pass
    assert "缺少授权提供者" in str(error.value.__cause__)
    assert app.state.bootstrap.definitions is None


def test_controller_requires_di_and_duplicate_operations_fail(module_package, config_dir):
    app = feature_app(module_package, config_dir)
    disabled = create_app(base_dir=app.state.bootstrap.base_dir, environ={"DI_ENABLED": "false"})
    with pytest.raises(BootstrapError) as error, TestClient(disabled):
        pass
    assert "要求启用 DI" in str(error.value.__cause__)
    router = APIRouter()
    router.add_api_route("/first", lambda: {}, operation_id="same")
    router.add_api_route("/second", lambda: {}, operation_id="same")
    with pytest.raises(ValueError, match="operationId"):
        app.state.web_routes.include(RouterRegistration(router))


def test_inherited_method_override_and_controller_lifecycle(module_package, config_dir):
    source = CONTROLLER.replace(
        "scope=ComponentScopeEnum.TRANSIENT",
        "scope=ComponentScopeEnum.SINGLETON",
    )
    source += """
@controller('/inherited')
class Child(Endpoints):
    def write(self, payload):
        return payload
"""
    app = feature_app(module_package, config_dir, source=source)
    with TestClient(app) as client:
        assert client.get("/inherited/3?q=1").json()["data"]["number"] == 3
        assert client.post("/inherited/write", json={}).json()["code"] == 405
        assert client.get("/transient").json() == client.get("/transient").json()


def test_protected_mount_is_rejected_instead_of_bypassing_dependency(config_dir):
    from starlette.responses import PlainTextResponse

    async def mounted(scope, receive, send):
        await PlainTextResponse("secret")(scope, receive, send)

    router = APIRouter()
    router.mount("/mounted", mounted)
    with pytest.raises(ValueError, match="Mount/WebSocket"):
        create_app(
            base_dir=config_dir(),
            environ={},
            access_provider=lambda: None,
            routers=[RouterRegistration(router, policy=RoutePolicy())],
        )


def test_explicit_registration_closes_after_startup(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    router = APIRouter()
    router.get("/late")(lambda: {})
    with TestClient(app):
        with pytest.raises(RuntimeError, match="启动前"):
            app.state.web_routes.include(RouterRegistration(router))


def test_multi_method_controller_has_distinct_openapi_operations(module_package, config_dir):
    source = CONTROLLER.replace(
        "@route('/write', methods=('POST',)", "@route('/write', methods=('POST', 'PUT')"
    )
    app = feature_app(module_package, config_dir, source=source)
    with TestClient(app) as client:
        for method in ("POST", "PUT"):
            assert (
                client.request(method, "/declared/write", json={"displayName": method}).json()[
                    "data"
                ]
                == method
            )
        operations = client.get("/openapi.json").json()["paths"]["/declared/write"]
        assert operations["post"]["operationId"] != operations["put"]["operationId"]


def test_ambiguous_native_operation_id_is_rejected(config_dir):
    router = APIRouter()
    router.add_api_route("/ambiguous", lambda: {}, methods=["GET", "POST"])
    with pytest.raises(ValueError, match="唯一标识"):
        create_app(base_dir=config_dir(), environ={}, routers=[RouterRegistration(router)])


async def _socket_endpoint(websocket):
    await websocket.accept()
    await websocket.close()


async def _socket_authorizer(websocket, endpoint):
    await endpoint(websocket)


def test_register_websocket_before_seal_reject_duplicates_and_after_seal(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    registrar = app.state.web_routes
    route = registrar.register_websocket(
        "/socket", _socket_endpoint, authorizer=_socket_authorizer, policy=RoutePolicy(), name="s1"
    )
    assert isinstance(route, AuthenticatedWebSocketRoute)
    assert route in app.routes
    with pytest.raises(ValueError, match="重复路由"):
        registrar.register_websocket(
            "/socket",
            _socket_endpoint,
            authorizer=_socket_authorizer,
            policy=RoutePolicy(),
            name="s2",
        )
    assert route in app.routes and app.routes.count(route) == 1
    registrar.unregister_websocket(route)
    assert route not in app.routes
    with TestClient(app):
        with pytest.raises(RuntimeError, match="已经发布"):
            registrar.register_websocket(
                "/socket2",
                _socket_endpoint,
                authorizer=_socket_authorizer,
                policy=RoutePolicy(),
                name="s3",
            )


def test_unregister_websocket_requires_ownership_and_rejects_after_seal(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    registrar = app.state.web_routes
    foreign = AuthenticatedWebSocketRoute(
        "/foreign", _socket_endpoint, authorizer=_socket_authorizer, policy=RoutePolicy()
    )
    with pytest.raises(RuntimeError, match="不属于当前未发布注册器"):
        registrar.unregister_websocket(foreign)
    route = registrar.register_websocket(
        "/owned", _socket_endpoint, authorizer=_socket_authorizer, policy=RoutePolicy()
    )
    with TestClient(app):
        with pytest.raises(RuntimeError, match="不属于当前未发布注册器"):
            registrar.unregister_websocket(route)


@pytest.mark.parametrize(
    "policy,authorizer",
    [
        (RoutePolicy.public(), _socket_authorizer),
        (RoutePolicy(), None),
    ],
)
def test_authenticated_websocket_route_requires_identity_and_authorizer(policy, authorizer):
    with pytest.raises(ValueError, match="必须声明独立认证适配器和受保护策略"):
        AuthenticatedWebSocketRoute(
            "/socket", _socket_endpoint, authorizer=authorizer, policy=policy
        )
