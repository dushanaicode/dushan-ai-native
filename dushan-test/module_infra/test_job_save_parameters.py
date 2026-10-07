from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from module_infra.controller.admin.job.vo.job.job_save_req_vo import JobSaveReqVO
from module_infra.service.job.job_service_impl import JobServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def payload():
    """构造真实保存 VO 的最小请求。"""
    return {
        "name": "测试任务",
        "handlerName": "test.job",
        "fanOut": False,
        "cronExpression": "0 0 * * *",
        "retryCount": 0,
        "retryInterval": 0,
    }


@pytest.mark.parametrize("parameter", [None, "", "{}", '{"count":2,"nested":{"enabled":true}}'])
def test_json_object_keeps_string_contract_and_empty_semantics(payload, parameter):
    """合法输入保持字符串协议及空参数语义，既有 Service 得到确定字典。"""
    request = JobSaveReqVO(**payload, handlerParam=parameter)
    assert request.handler_param == parameter
    service = JobServiceImpl()
    service.tenant = SimpleNamespace(get_required_tenant_id=Mock(return_value="1"))
    row = service._row(request, 1, 1)
    assert row.handler_param == parameter
    assert row.parameters == (
        {"count": 2, "nested": {"enabled": True}} if parameter and "count" in parameter else {}
    )


@pytest.mark.parametrize(
    "parameter", ["[]", "null", "42", "true", '"text"', "{", "dushan_job", " ", {"count": 2}]
)
async def test_invalid_parameters_are_field_errors_before_service(payload, parameter):
    """非法 JSON 和非对象通过统一字段错误返回，业务保存不会运行。"""
    app = FastAPI()
    GlobalExceptionHandler().register(app)
    save = Mock()

    @app.post("/job")
    async def create(request: JobSaveReqVO):
        """使用实际请求模型验证字段边界。"""
        save(request)
        return {"code": 0}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/job", json={**payload, "handlerParam": parameter})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == GlobalErrorCodeConstants.VALIDATION_ERROR.code
    assert body["error"]["fields"][0]["field"] == "handlerParam"
    save.assert_not_called()
