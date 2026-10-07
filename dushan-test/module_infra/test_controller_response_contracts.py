import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from module_infra.controller.admin.cache.cache_controller import CacheController, cache_controller
from module_infra.controller.admin.cache.vo.monitor.command_stat_vo import CommandStatVO
from module_infra.controller.admin.cache.vo.monitor.monitor_resp_vo import MonitorRespVO
from module_infra.controller.admin.config.config_type_controller import (
    ConfigTypeController,
    config_type_controller,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    (
        "router",
        "path",
        "endpoint",
        "service_parameter",
        "method",
        "value",
        "response_type",
        "expected",
    ),
    [
        (
            config_type_controller,
            "/config/type/simple-list",
            ConfigTypeController.get_simple_config_type_list,
            "config_type_service",
            "get_config_type_list",
            [
                SimpleNamespace(
                    id=9_007_199_254_740_993,
                    module="infra",
                    name="基础配置",
                    code="infra_config",
                )
            ],
            "ConfigTypeSimpleRespVO",
            [
                {
                    "id": "9007199254740993",
                    "module": "infra",
                    "name": "基础配置",
                    "code": "infra_config",
                }
            ],
        ),
        (
            cache_controller,
            "/cache/get-monitor-info",
            CacheController.get_cache_monitor_info,
            "cache_service",
            "get_cache_monitor_info",
            MonitorRespVO(
                info={"redis_version": "7.0", "connected_clients": 2, "role": "master"},
                db_size=7,
                command_stats=[CommandStatVO(command="get", calls=3, usec=12)],
            ),
            "MonitorRespVO",
            {
                "info": {"redis_version": "7.0", "connected_clients": 2, "role": "master"},
                "dbSize": 7,
                "commandStats": [{"command": "get", "calls": 3, "usec": 12}],
            },
        ),
    ],
)
async def test_controller_response_schema_and_serialization(
    router, path, endpoint, service_parameter, method, value, response_type, expected
):
    app = FastAPI()
    app.include_router(router)
    service = SimpleNamespace(**{method: AsyncMock(return_value=value)})
    dependency = inspect.signature(endpoint).parameters[service_parameter].default.dependency
    app.dependency_overrides[dependency] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
        if router is config_type_controller:
            assert (await client.get("/config/type/list-all-simple")).status_code == 404

    assert response.status_code == 200, response.text
    assert response.json()["data"] == expected
    schema = app.openapi()
    result_ref = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    result_schema = schema["components"]["schemas"][result_ref.rsplit("/", 1)[1]]
    data_schema = result_schema["properties"]["data"]["anyOf"][0]
    expected_schema = {"$ref": f"#/components/schemas/{response_type}"}
    if isinstance(expected, list):
        assert data_schema["items"] == expected_schema
    else:
        assert data_schema == expected_schema
