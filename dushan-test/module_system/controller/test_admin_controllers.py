"""校验原生路由装配覆盖全部 Admin 控制器，并保留明确的访问策略。"""

import importlib
import pkgutil

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute, _iter_routes_with_context

from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.router import admin_router_main

pytestmark = pytest.mark.unit


def _discover() -> set:
    package = importlib.import_module("module_system.controller.admin")
    found = set()
    for info in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
        if not info.name.endswith("_controller"):
            continue
        module = importlib.import_module(info.name)
        for value in vars(module).values():
            if isinstance(value, APIRouter):
                found.update(
                    route.endpoint for route in value.routes if isinstance(route, APIRoute)
                )
    return found


def test_listed_controllers_match_actual_code():
    actual = {
        route.endpoint
        for route, _ in _iter_routes_with_context(admin_router_main.routes)
        if isinstance(route, APIRoute)
    }
    assert actual == _discover()


def test_every_controller_uses_shared_prefix():
    assert admin_router_main.routes
    assert all(
        (context.path if context else route.path).startswith("/admin-api/system/")
        for route, context in _iter_routes_with_context(admin_router_main.routes)
    )


def test_controller_entries_have_explicit_access_policy():
    for endpoint in _discover():
        assert isinstance(getattr(endpoint, RoutePolicy.ATTRIBUTE, None), RoutePolicy), endpoint


@pytest.mark.parametrize("module_name", ["module_system", "module_infra"])
def test_routes_follow_business_domains_without_duplicate_entries(module_name):
    mounted = set()
    for router in importlib.import_module(f"{module_name}.router").routers:
        for route, context in _iter_routes_with_context(router.routes):
            if not isinstance(route, APIRoute):
                continue
            path = context.path if context else route.path
            domain = route.endpoint.__module__.split(".controller.", 1)[1].split(".")[1]
            assert path.split("/")[3] == domain.replace("_", "-"), (path, domain)
            for method in route.methods:
                entry = (method, path)
                assert entry not in mounted, entry
                mounted.add(entry)
