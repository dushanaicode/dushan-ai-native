import sys

import pytest
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from server.bootstrap.bootstrap_error import BootstrapError

pytestmark = pytest.mark.unit

ROUTER = (
    "from fastapi import APIRouter\n"
    "\n"
    "from framework.starter_web.public import Result, RoutePolicy\n"
    "\n"
    "plug_router = APIRouter(prefix='/plug-api/{name}')\n"
    "\n"
    "\n"
    "@plug_router.get('/ping')\n"
    "@RoutePolicy.public()\n"
    "async def ping():\n"
    "    return Result.success(data='{name}')\n"
    "\n"
    "\n"
    "routers = [plug_router]\n"
)


def application(config_dir, packages, enabled):
    values = {"modules": {"packages": ["framework", *packages], "enabled": ["framework", *enabled]}}
    return create_public_app(base_dir=config_dir(values), environ={})


def test_enabled_module_routes_are_published_and_withdrawn(module_package, config_dir):
    module_package(
        "plug_alpha",
        scan_roots=(),
        routers=("router:routers",),
        files={"router.py": ROUTER.format(name="alpha")},
    )
    app = application(config_dir, ["plug_alpha"], ["plug_alpha"])
    assert "plug_alpha.router" not in sys.modules
    for _ in range(2):
        with TestClient(app) as client:
            assert client.get("/plug-api/alpha/ping").json()["data"] == "alpha"
        assert not any(getattr(route, "path", "") == "/plug-api/alpha/ping" for route in app.routes)


def test_disabled_module_router_is_not_imported(module_package, config_dir):
    module_package(
        "plug_beta",
        scan_roots=(),
        routers=("router:routers",),
        files={"router.py": "raise AssertionError('未启用模块不应导入')"},
    )
    app = application(config_dir, ["plug_beta"], [])
    with TestClient(app):
        assert not any(
            str(getattr(route, "path", "")).startswith("/plug-api") for route in app.routes
        )
    assert "plug_beta.router" not in sys.modules


def test_router_declaration_must_point_to_router_list(module_package, config_dir):
    module_package(
        "plug_gamma",
        scan_roots=(),
        routers=("router:routers",),
        files={"router.py": "routers = ['not-a-router']\n"},
    )
    app = application(config_dir, ["plug_gamma"], ["plug_gamma"])
    with pytest.raises(BootstrapError) as caught, TestClient(app):
        pass
    assert "APIRouter" in str(caught.value.__cause__)
