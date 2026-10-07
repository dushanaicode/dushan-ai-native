import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from module_system.controller.admin.oauth2.oauth2_open_controller import (
    Oauth2OpenController,
    oauth2_open_controller,
)

pytestmark = pytest.mark.unit


async def test_authorize_info_response_schema_and_serialization():
    app = FastAPI()
    app.include_router(oauth2_open_controller)
    services = {
        "oauth2_client_service": SimpleNamespace(
            validate_client=AsyncMock(
                return_value=SimpleNamespace(name="测试应用", logo="", scopes=["read"])
            )
        ),
        "oauth2_approve_service": SimpleNamespace(get_approve_list=AsyncMock(return_value=[])),
        "security": SimpleNamespace(require=lambda: SimpleNamespace(account_id="123")),
    }
    parameters = inspect.signature(Oauth2OpenController.authorize).parameters

    def override(service):
        return lambda: service

    for name, service in services.items():
        app.dependency_overrides[parameters[name].default.dependency] = override(service)

    path = "/oauth2/open/authorize"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path, params={"client_id": "client"})

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "client": {"name": "测试应用", "logo": ""},
        "scopes": [{"key": "read", "value": "False"}],
    }
    schema = app.openapi()
    result_ref = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    result_schema = schema["components"]["schemas"][result_ref.rsplit("/", 1)[1]]
    assert result_schema["properties"]["data"]["anyOf"][0] == {
        "$ref": "#/components/schemas/OAuth2OpenAuthorizeInfoRespVO"
    }
