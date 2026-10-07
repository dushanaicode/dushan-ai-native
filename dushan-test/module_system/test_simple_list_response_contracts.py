import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from module_system.controller.admin.dict.dict_data_controller import (
    DictDataController,
    dict_data_controller,
)
from module_system.controller.admin.dict.dict_type_controller import (
    DictTypeController,
    dict_type_controller,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("router", "endpoint", "service_parameter", "method", "record", "response_type", "expected"),
    [
        (
            dict_data_controller,
            DictDataController.get_simple_dict_data_list,
            "dict_data_service",
            "get_dict_data_list",
            SimpleNamespace(
                id=9_007_199_254_740_993,
                dict_type="test_status",
                value="1",
                label="启用",
                color_type="success",
                tag_style={"fontWeight": "bold"},
                permission="system:user:query",
            ),
            "DictDataSimpleRespVO",
            {
                "dictType": "test_status",
                "value": "1",
                "label": "启用",
                "colorType": "success",
                "tagStyle": {"fontWeight": "bold"},
                "permission": "system:user:query",
            },
        ),
        (
            dict_type_controller,
            DictTypeController.get_simple_dict_type_list,
            "dict_type_service",
            "get_dict_type_list",
            SimpleNamespace(id=9_007_199_254_740_993, name="状态", type="test_status"),
            "DictTypeSimpleRespVO",
            {"id": "9007199254740993", "name": "状态", "type": "test_status"},
        ),
    ],
)
async def test_simple_list_response_schema_and_serialization(
    router, endpoint, service_parameter, method, record, response_type, expected
):
    app = FastAPI()
    app.include_router(router)
    path = router.prefix + "/simple-list"
    service = SimpleNamespace(**{method: AsyncMock(return_value=[record])})
    dependency = inspect.signature(endpoint).parameters[service_parameter].default.dependency
    app.dependency_overrides[dependency] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
        if router is dict_type_controller:
            assert (await client.get("/dict/type/list-all-simple")).status_code == 404

    assert response.status_code == 200, response.text
    assert response.json()["data"] == [expected]
    schema = app.openapi()
    result_ref = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    result_schema = schema["components"]["schemas"][result_ref.rsplit("/", 1)[1]]
    data_schema = result_schema["properties"]["data"]["anyOf"][0]
    assert data_schema["items"] == {"$ref": f"#/components/schemas/{response_type}"}
