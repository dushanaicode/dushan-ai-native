from typing import Annotated

import pytest
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient
from starlette.background import BackgroundTask
from starlette.responses import PlainTextResponse, StreamingResponse

from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.exception.reported_http_failure import ReportedHttpFailure
from framework.starter_web.files.local_files import LocalFiles
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.router_registration import RouterRegistration
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app


def public_app(config_dir, **kwargs):
    app = create_app(base_dir=config_dir(), environ={"SERVER_ENGINE": "uvicorn"}, **kwargs)
    RoutePolicy.public()(app.router)
    return app


def test_unclassified_is_rejected_and_public_is_explicit(config_dir):
    app = create_app(base_dir=config_dir(), environ={})
    app.get("/unclassified")(lambda: {})
    with pytest.raises(BootstrapError, match="Web 路由") as result, TestClient(app):
        pass
    assert "尚未声明" in str(result.value.__cause__)
    app = create_app(base_dir=config_dir(), environ={})
    app.get("/public")(RoutePolicy.public()(lambda: {}))
    with TestClient(app) as client:
        assert client.get("/public").json() == {}
        assert (
            client.get("/openapi.json").json()["paths"]["/public"]["get"]["x-route-access"]["mode"]
            == "public"
        )


def test_protected_source_mutation_before_and_after_seal(config_dir):
    router = APIRouter()
    router.get("/protected")(lambda: {})

    async def leak(request):
        return PlainTextResponse("leaked")

    app = public_app(
        config_dir,
        routers=[RouterRegistration(router, policy=RoutePolicy())],
        access_provider=lambda: None,
    )
    router.add_route("/leak", leak)
    with pytest.raises(BootstrapError) as result, TestClient(app):
        pass
    assert "独立授权" in str(result.value.__cause__)

    router = APIRouter()
    router.get("/protected")(lambda: {})
    app = public_app(
        config_dir,
        routers=[RouterRegistration(router, policy=RoutePolicy())],
        access_provider=lambda: None,
    )
    with TestClient(app) as client:
        document = app.openapi()
        router.add_route("/leak", leak)
        router.get("/late")(lambda: {})
        assert client.get("/protected").json()["code"] == 401
        assert client.get("/leak").json()["code"] == 404
        assert client.get("/late").json()["code"] == 404
        assert app.openapi() is document
        for modify in (
            lambda: app.add_api_route("/after", lambda: {}),
            lambda: app.include_router(APIRouter()),
            lambda: app.mount("/after", app),
            lambda: app.router.routes.clear(),
        ):
            with pytest.raises(RuntimeError, match="已经发布"):
                modify()


def test_shadow_and_openapi_conflicts_are_distinct(config_dir):
    router = APIRouter()
    router.get("/users/{user_id}")(lambda user_id: user_id)
    router.get("/users/me")(lambda: "me")
    with pytest.raises(ValueError, match="遮蔽"):
        public_app(config_dir, routers=[RouterRegistration(router, policy=RoutePolicy.public())])
    first, second = APIRouter(), APIRouter()
    first.get("/items/{item_id:int}", include_in_schema=False)(lambda item_id: {"int": item_id})
    second.get("/items/{slug}", include_in_schema=False)(lambda slug: {"slug": slug})
    app = public_app(config_dir, routers=[RouterRegistration(first), RouterRegistration(second)])
    with TestClient(app) as client:
        assert client.get("/items/12").json() == {"int": 12}
        assert client.get("/items/name").json() == {"slug": "name"}
    first, second = APIRouter(), APIRouter()
    first.get("/items/{item_id:int}")(lambda item_id: {})
    second.get("/items/{slug}")(lambda slug: {})
    with pytest.raises(ValueError, match="OpenAPI 路径模板冲突"):
        public_app(config_dir, routers=[RouterRegistration(first), RouterRegistration(second)])


def test_form_only_router_is_adapted_and_closes_extra_upload(config_dir):
    router = APIRouter()
    captured = []

    @router.post("/form")
    async def form(request: Request, name: Annotated[str, Form()]):
        data = await request.form()
        captured.append(data["extra"].file)
        return {"name": name, "request_type": type(request).__name__}

    app = public_app(config_dir, routers=[RouterRegistration(router)])
    with TestClient(app) as client:
        response = client.post("/form", files={"name": (None, "test"), "extra": ("a.bin", b"abc")})
        assert response.json() == {"name": "test", "request_type": "WebRequest"}
    assert captured[0].closed


def test_missing_file_is_business_not_found(config_dir, tmp_path):
    app = public_app(config_dir)
    files = LocalFiles(tmp_path, FileResult(app.state.bootstrap.response_settings))
    (tmp_path / "directory").mkdir()
    app.get("/files/{name}")(lambda name: files.download(name))
    with TestClient(app) as client:
        for name in ("missing.bin", "directory"):
            response = client.get("/files/" + name)
            assert response.status_code == 200 and response.json()["code"] == 404


def test_stream_failure_and_background_error_semantics(config_dir, capsys):
    app = public_app(config_dir)

    @app.get("/stream")
    async def stream(before: bool = False):
        async def chunks():
            try:
                if before:
                    raise ValueError("password=hidden")
                yield b"first"
                raise ValueError("password=hidden")
            finally:
                assert RequestContext.current().connection.app is app

        return StreamingResponse(chunks(), media_type="text/plain")

    @app.get("/background")
    async def background():
        async def failed():
            raise ValueError("password=background-secret")

        return Response("complete", background=BackgroundTask(failed))

    with TestClient(app) as client:
        assert client.get("/stream?before=true").json()["code"] == 500
        with pytest.raises(ReportedHttpFailure):
            client.get("/stream")
        capsys.readouterr()
        assert client.get("/background").text == "complete"
        output = capsys.readouterr().out
        assert "outcome=failed_after_response" in output
        assert "background-secret" not in output


def test_business_outcome_does_not_require_body_parsing(config_dir, capsys):
    app = public_app(config_dir)
    app.get("/result")(lambda: Result(code=42, message="known error"))

    @app.get("/error")
    async def failure():
        raise HTTPException(409)

    with TestClient(app) as client:
        capsys.readouterr()
        client.get("/result")
        client.get("/error")
        output = capsys.readouterr().out
    assert "business_code=42" in output and "business_code=409" in output
    assert "outcome=completed" in output


def test_protection_uses_verified_ip_for_subject_and_key(config_dir):
    from framework.starter_protection.core.protection_key import ProtectionKey
    from framework.starter_protection.web.protection_invocation import ProtectionInvocation

    async def protected(request: Request):
        pass

    invocation = ProtectionInvocation(protected, (), None)
    app = create_app(
        base_dir=config_dir(
            {"config": {"models": {"ip": {"trusted_proxy_cidrs": ["127.0.0.1/32"]}}}}
        ),
        environ={},
    )

    @app.get("/subject")
    @RoutePolicy.public()
    async def subject(request: Request):
        service, identity, parameters = invocation.resolve((request,), {})
        assert service is request.app.state.protection
        return {
            "subject": identity.identifier,
            "key": ProtectionKey.build("ip-check", identity, parameters, 4096),
        }

    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        a = client.get("/subject", headers={"X-Forwarded-For": "203.0.113.1"}).json()
        b = client.get("/subject", headers={"X-Forwarded-For": "203.0.113.2"}).json()
        assert a["subject"] == "203.0.113.1" and b["subject"] == "203.0.113.2"
        assert a["key"] != b["key"]
    with TestClient(app, client=("198.51.100.1", 1234)) as client:
        a = client.get("/subject", headers={"X-Forwarded-For": "203.0.113.1"}).json()
        b = client.get("/subject", headers={"X-Forwarded-For": "203.0.113.2"}).json()
        assert a["subject"] == b["subject"] == "198.51.100.1"
        assert a["key"] == b["key"]


def test_nested_router_snapshot_preserves_lifespan_dependencies_and_policies(config_dir):
    from contextlib import asynccontextmanager

    from fastapi import Depends

    events = []

    @asynccontextmanager
    async def lifespan(app):
        events.append("open")
        yield
        events.append("close")

    async def dependency():
        events.append("dependency")

    child = APIRouter(prefix="/child", dependencies=[Depends(dependency)], lifespan=lifespan)
    RoutePolicy()(child)
    child.get("/secure")(lambda: {})
    parent = APIRouter(prefix="/parent")
    parent.include_router(child)
    parent.get("/public", dependencies=[Depends(dependency)])(lambda: {})
    app = public_app(config_dir, routers=[RouterRegistration(parent)], access_provider=lambda: None)
    with TestClient(app) as client:
        assert events == ["open"]
        assert client.get("/parent/child/secure").json()["code"] == 401
        assert client.get("/parent/public").json() == {}
        assert events == ["open", "dependency"]
        child.get("/late")(lambda: {})
        assert client.get("/parent/child/late").json()["code"] == 404
        operation = app.openapi()["paths"]["/parent/child/secure"]["get"]
        assert operation["x-route-access"]["mode"] == "protected"
    assert events == ["open", "dependency", "close"]


def test_operation_metadata_is_available_without_payload_capture(config_dir, capsys):
    from framework.starter_web.routing.access_log_policy import AccessLogPolicy
    from framework.starter_web.routing.operate_type_enum import OperateTypeEnum

    policy = AccessLogPolicy(
        enabled=True,
        operate_module="infra",
        operate_name="export-files",
        operate_type=OperateTypeEnum.EXPORT,
    )
    app = public_app(config_dir)

    @app.get("/export")
    @policy
    async def export():
        return Result.success(None)

    with TestClient(app) as client:
        capsys.readouterr()
        assert client.get("/export").json()["code"] == 0
        output = capsys.readouterr().out
        assert "operation=infra/export-files/5" in output
        endpoint = next(route.endpoint for route in app.routes if route.path == "/export")
        assert getattr(endpoint, AccessLogPolicy.ATTRIBUTE) == policy
    with pytest.raises(TypeError):
        AccessLogPolicy(request_enable=True)


def test_native_asgi_route_keeps_any_method_and_safe_template(config_dir, capsys):
    router = APIRouter()
    router.add_route("/raw/{capability}", PlainTextResponse("native ASGI"))
    app = public_app(config_dir, routers=[RouterRegistration(router)])
    with TestClient(app) as client:
        capsys.readouterr()
        assert client.request("REPORT", "/raw/private-capability").text == "native ASGI"
        output = capsys.readouterr().out
        assert "/raw/{capability}" in output and "private-capability" not in output
    router.add_api_route(
        "/raw/{capability}", lambda capability: {}, methods=["REPORT"], include_in_schema=False
    )
    with pytest.raises(ValueError, match="重复路由"):
        public_app(config_dir, routers=[RouterRegistration(router)])
