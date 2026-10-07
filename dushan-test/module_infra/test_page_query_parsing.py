from datetime import datetime
from inspect import signature

import pytest
from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from fastapi.params import Query as QueryParam
from fastapi.testclient import TestClient

from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from module_infra.controller.admin.codegen.codegen_controller import CodegenController
from module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo import CodegenTablePageReqVO
from module_infra.controller.admin.config.config_data_controller import ConfigDataController
from module_infra.controller.admin.config.config_type_controller import ConfigTypeController
from module_infra.controller.admin.config.vo.data.config_data_page_req_vo import ConfigDataPageReqVO
from module_infra.controller.admin.config.vo.type.config_type_page_req_vo import ConfigTypePageReqVO
from module_infra.controller.admin.data_source.data_source_config_controller import (
    DataSourceConfigController,
)
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)
from module_infra.controller.admin.file.file_config_controller import FileConfigController
from module_infra.controller.admin.file.file_controller import FileController
from module_infra.controller.admin.file.vo.config.file_config_page_req_vo import FileConfigPageReqVO
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.controller.admin.job.job_controller import JobController
from module_infra.controller.admin.job.job_log_controller import JobLogController
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO
from module_infra.controller.admin.logger.api_access_log_controller import ApiAccessLogController
from module_infra.controller.admin.logger.api_error_log_controller import ApiErrorLogController
from module_infra.controller.admin.logger.vo.api_access_log.api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)
from module_infra.controller.admin.mq.mq_controller import MqController
from module_infra.controller.admin.mq.mq_log_controller import MqLogController
from module_infra.controller.admin.mq.vo.log.mq_log_page_req_vo import MqLogPageReqVO
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO

pytestmark = pytest.mark.unit

PAGE_ENDPOINTS = (
    (ConfigDataController.get_config_page, ConfigDataPageReqVO),
    (ConfigTypeController.page_config_types, ConfigTypePageReqVO),
    (JobController.get_job_page, JobPageReqVO),
    (JobLogController.get_job_log_page, JobLogPageReqVO),
    (ApiErrorLogController.get_api_error_log_page, ApiErrorLogPageReqVO),
    (ApiAccessLogController.get_api_access_log_page, ApiAccessLogPageReqVO),
    (CodegenController.get_codegen_table_page, CodegenTablePageReqVO),
    (FileController.get_file_page, FilePageReqVO),
    (FileConfigController.get_file_config_page, FileConfigPageReqVO),
    (MqLogController.get_log_page, MqLogPageReqVO),
    (DataSourceConfigController.get_data_source_config_page, DataSourceConfigPageReqVO),
    (MqController.get_mq_definition_page, MqPageReqVO),
)
PAGE_MODELS = tuple(model for _, model in PAGE_ENDPOINTS)
RANGE_FIELDS = (
    (ConfigDataPageReqVO, "create_time"),
    (ConfigTypePageReqVO, "create_time"),
    (JobPageReqVO, "create_time"),
    (ApiErrorLogPageReqVO, "exception_time"),
    (ApiAccessLogPageReqVO, "begin_time"),
    (CodegenTablePageReqVO, "create_time"),
    (FilePageReqVO, "create_time"),
    (FileConfigPageReqVO, "create_time"),
    (DataSourceConfigPageReqVO, "create_time"),
    (MqPageReqVO, "create_time"),
)


def parsing_app(model_class, *, business_errors=False):
    app = FastAPI()
    if business_errors:
        GlobalExceptionHandler(debug=False).register(app)

    @app.get("/query")
    def query(page_req_vo: model_class = Query()):
        # dict(model) 保留 exclude=True 的时间筛选，确保断言涵盖真实请求字段。
        return jsonable_encoder(dict(page_req_vo), by_alias=False)

    return app


@pytest.fixture(params=PAGE_MODELS, ids=lambda model: model.__name__)
def page_client(request):
    with TestClient(parsing_app(request.param)) as client:
        yield client


@pytest.mark.parametrize("params", [[], [("page", "2"), ("pageSize", "25")]])
def test_page_defaults_and_camel_case(page_client, params):
    query = page_client.get("/query", params=params)
    assert query.status_code == 200
    assert query.json()["page"] == (2 if params else 1)
    assert query.json()["page_size"] == (25 if params else None)


@pytest.mark.parametrize("values", [["1", "2"], ["1", "1"]])
def test_duplicate_scalar_page_uses_last_value(page_client, values):
    params = [("page", value) for value in values]
    query = page_client.get("/query", params=params)
    assert query.status_code == 200
    assert query.json()["page"] == int(values[-1])


def test_python_page_size_field_name(page_client):
    query = page_client.get("/query?page_size=25")
    assert query.status_code == 200
    assert query.json()["page_size"] == 25


@pytest.mark.parametrize(
    "params, error_type",
    [([("page", "bad")], "int_parsing"), ([("pageSize", "0")], "greater_than_equal")],
)
def test_validation_errors_keep_query_location(page_client, params, error_type):
    query = page_client.get("/query", params=params)
    assert query.status_code == 422
    error = query.json()["detail"][0]
    assert error["loc"] == ["query", params[0][0]]
    assert error["type"] == error_type
    assert error["input"] == params[0][1]


@pytest.mark.parametrize(
    "model_class, field_name", RANGE_FIELDS, ids=lambda item: getattr(item, "__name__", item)
)
@pytest.mark.parametrize(
    "values",
    [
        ["2026-01-01T00:00:00", "2026-01-02T00:00:00"],
        ["2026-01-01T00:00:00", "2026-01-01T00:00:00"],
    ],
    ids=["range", "duplicates"],
)
def test_time_ranges_preserve_two_values_duplicates_and_aliases(model_class, field_name, values):
    alias = model_class.model_fields[field_name].alias
    with TestClient(parsing_app(model_class)) as client:
        params = [(alias, value) for value in values]
        query = client.get("/query", params=params)
    assert query.status_code == 200
    assert query.json()[field_name] == values


@pytest.mark.parametrize(
    "model_class, field_name",
    RANGE_FIELDS,
    ids=lambda item: getattr(item, "__name__", item),
)
def test_invalid_time_range_preserves_query_item_location(model_class, field_name):
    alias = model_class.model_fields[field_name].alias
    with TestClient(parsing_app(model_class)) as client:
        params = [(alias, "2026-01-01T00:00:00"), (alias, "bad")]
        query = client.get("/query", params=params)
    assert query.status_code == 422
    assert query.json()["detail"][0]["loc"] == ["query", alias, 1]


@pytest.mark.parametrize("model_class, field_name", RANGE_FIELDS)
@pytest.mark.parametrize(
    "values",
    [
        ["2026-01-01T00:00:00"],
        ["2026-01-01T00:00:00", "2026-01-02T00:00:00", "2026-01-03T00:00:00"],
        ["2026-01-02T00:00:00", "2026-01-01T00:00:00"],
    ],
    ids=["single", "three", "reversed"],
)
def test_time_ranges_reject_incomplete_extra_and_reversed_values(model_class, field_name, values):
    alias = model_class.model_fields[field_name].alias
    with TestClient(parsing_app(model_class)) as client:
        query = client.get("/query", params=[(alias, value) for value in values])
    assert query.status_code == 422
    assert query.json()["detail"][0]["loc"][:2] == ["query", alias]


def test_file_type_explicit_alias_and_config_id():
    with TestClient(parsing_app(FilePageReqVO)) as client:
        query = client.get("/query?type=jpg&configId=1024")
    assert query.status_code == 200
    assert query.json()["file_type"] == "jpg"
    assert query.json()["config_id"] == 1024


@pytest.mark.parametrize("model_class", [JobLogPageReqVO, MqLogPageReqVO])
def test_log_times_remain_separate_scalar_fields(model_class):
    params = [("beginTime", "2026-01-01T00:00:00"), ("endTime", "2026-01-02T00:00:00")]
    with TestClient(parsing_app(model_class)) as client:
        query = client.get("/query", params=params)
    assert query.status_code == 200
    assert datetime.fromisoformat(query.json()["begin_time"]) < datetime.fromisoformat(
        query.json()["end_time"]
    )


@pytest.mark.parametrize("model_class", PAGE_MODELS, ids=lambda model: model.__name__)
def test_public_validation_error_response(model_class):
    with TestClient(parsing_app(model_class, business_errors=True)) as client:
        query = client.get("/query?page=bad")
    assert query.status_code == 200
    assert query.json()["code"] != 0
    error = query.json()["error"]["fields"][0]
    assert error["field"] == "page"
    assert "input" not in error


@pytest.mark.parametrize("endpoint, model_class", PAGE_ENDPOINTS, ids=lambda item: item.__name__)
def test_page_controllers_bind_query_model(endpoint, model_class):
    parameters = signature(endpoint).parameters
    assert parameters["page_req_vo"].annotation is model_class
    assert isinstance(parameters["page_req_vo"].default, QueryParam)
    assert "request" not in parameters
