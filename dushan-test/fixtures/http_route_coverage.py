import json
from pathlib import Path

from fastapi.routing import APIRoute, _iter_routes_with_context
from starlette.routing import compile_path

from framework.starter_web.context.http_observation import HttpObservation


class HttpRouteCoverage:
    routes: dict[tuple[str, str], set[tuple[int, int | None]]] = {}
    patterns = {}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        finally:
            if scope["type"] == "http":
                observation = HttpObservation.find(scope)
                if observation is not None:
                    for key, pattern in self.patterns.items():
                        if key[0] == scope["method"] and pattern.fullmatch(scope["path"]):
                            self.routes[key].add((observation.status, observation.business_code))
                            break

    @classmethod
    def register(cls, app):
        for route, context in _iter_routes_with_context(app.routes):
            if not isinstance(route, APIRoute):
                continue
            path = context.path if context else route.path
            if path.startswith(("/admin-api/system/", "/admin-api/infra/", "/weapp-api/infra/")):
                for method in route.methods:
                    cls.routes.setdefault((method, path), set())
                    cls.patterns[(method, path)] = compile_path(path)[0]

    @classmethod
    def save(cls, path):
        records = [
            {
                "method": method,
                "path": route,
                "outcomes": [
                    {"http_status": status, "business_code": code}
                    for status, code in sorted(outcomes, key=str)
                ],
            }
            for (method, route), outcomes in sorted(cls.routes.items())
        ]
        Path(path).write_text(json.dumps(records, indent=2), encoding="utf-8")
