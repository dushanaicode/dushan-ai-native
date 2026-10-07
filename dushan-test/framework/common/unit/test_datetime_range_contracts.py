import importlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from framework.common.contracts import DateTimeRangeInput
from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from module_system.controller.admin.user.vo.user.user_export_req_vo import UserExportReqVO
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO

pytestmark = pytest.mark.unit

START = "2026-01-01T00:00:00"
END = "2026-01-02T00:00:00"
ADAPTER = TypeAdapter(DateTimeRangeInput)
RANGE_REQUESTS = (
    (
        "module_system.controller.admin.notification.vo.notice.notice_page_req_vo",
        "NoticePageReqVO",
        "create_time",
    ),
    (
        "module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo",
        "CodegenTablePageReqVO",
        "create_time",
    ),
    (
        "module_infra.controller.admin.config.vo.data.config_data_page_req_vo",
        "ConfigDataPageReqVO",
        "create_time",
    ),
    (
        "module_infra.controller.admin.config.vo.type.config_type_page_req_vo",
        "ConfigTypePageReqVO",
        "create_time",
    ),
    (
        "module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo",
        "DataSourceConfigPageReqVO",
        "create_time",
    ),
    (
        "module_infra.controller.admin.file.vo.config.file_config_page_req_vo",
        "FileConfigPageReqVO",
        "create_time",
    ),
    ("module_infra.controller.admin.file.vo.file.file_page_req_vo", "FilePageReqVO", "create_time"),
    ("module_infra.controller.admin.job.vo.job.job_page_req_vo", "JobPageReqVO", "create_time"),
    (
        "module_infra.controller.admin.logger.vo.api_access_log.api_access_log_page_req_vo",
        "ApiAccessLogPageReqVO",
        "begin_time",
    ),
    (
        "module_infra.controller.admin.logger.vo.api_error_log.api_error_log_page_req_vo",
        "ApiErrorLogPageReqVO",
        "exception_time",
    ),
    ("module_infra.controller.admin.mq.vo.mq.mq_page_req_vo", "MqPageReqVO", "create_time"),
    (
        "module_system.controller.admin.announcement.vo.announcement_page_req_vo",
        "AnnouncementPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.dept.vo.post.post_page_req_vo",
        "PostPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.dict.vo.data.dict_data_page_req_vo",
        "DictDataPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.dict.vo.type.dict_type_page_req_vo",
        "DictTypePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.logger.vo.login_log.login_log_page_req_vo",
        "LoginLogPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.logger.vo.operate_log.operate_log_page_req_vo",
        "OperateLogPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.mail.vo.template.mail_template_page_req_vo",
        "MailTemplatePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo",
        "NoticeLogPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo",
        "NoticeMessageMyPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo",
        "NoticeMessagePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.oauth2.vo.client.oauth2_client_page_req_vo",
        "OAuth2ClientPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.oauth2.vo.token.oauth2_access_token_page_req_vo",
        "OAuth2AccessTokenPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.permission.vo.role.role_page_req_vo",
        "RolePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.sms.vo.channel.sms_channel_page_req_vo",
        "SmsChannelPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.sms.vo.log.sms_log_page_req_vo",
        "SmsLogPageReqVO",
        "send_time",
    ),
    (
        "module_system.controller.admin.sms.vo.log.sms_log_page_req_vo",
        "SmsLogPageReqVO",
        "receive_time",
    ),
    (
        "module_system.controller.admin.sms.vo.template.sms_template_page_req_vo",
        "SmsTemplatePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.social.vo.client.social_client_page_req_vo",
        "SocialClientPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.social.vo.user.social_user_page_req_vo",
        "SocialUserPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.tenant.vo.package.tenant_package_page_req_vo",
        "TenantPackagePageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo",
        "TenantPageReqVO",
        "create_time",
    ),
    (
        "module_system.controller.admin.user.vo.user.user_page_req_vo",
        "UserPageReqVO",
        "create_time",
    ),
)


@pytest.mark.parametrize(
    "value",
    [
        [],
        [START],
        [START, END, END],
        [END, START],
        [None, END],
        [START, None],
        ["", END],
        [START, ""],
        ["bad", END],
        ["0001-01-01T00:00:00+01:00", END],
        [START, "9999-12-31T23:59:59-01:00"],
    ],
)
def test_invalid_ranges_are_rejected_before_querying(value):
    """非法长度、端点、顺序与 UTC 溢出都必须是输入校验错误。"""
    with pytest.raises(ValidationError):
        ADAPTER.validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value, expected",
    [
        ([START, END], (datetime(2026, 1, 1), datetime(2026, 1, 2))),
        ([START, START], (datetime(2026, 1, 1), datetime(2026, 1, 1))),
        (
            ["2026-01-01T08:00:00+08:00", "2026-01-01T00:00:00Z"],
            (datetime(2026, 1, 1), datetime(2026, 1, 1)),
        ),
        (
            ["2026-01-01T08:00:00+08:00", "2026-01-01T00:00:01"],
            (datetime(2026, 1, 1), datetime(2026, 1, 1, 0, 0, 1)),
        ),
        ((datetime.min, datetime.max), (datetime.min, datetime.max)),
    ],
)
def test_valid_ranges_normalize_instants_and_preserve_inclusive_boundaries(value, expected):
    """闭区间支持相等端点，并按 UTC 时刻比较混合偏移输入。"""
    result = ADAPTER.validate_python(value)
    assert isinstance(result, DateTimeRangeInput)
    assert result == expected


def test_offset_order_is_checked_after_normalization():
    """拒绝表面钟点递增、实际时刻递减的范围。"""
    with pytest.raises(ValidationError, match="开始时间不能晚于结束时间"):
        ADAPTER.validate_python(["2026-01-01T08:00:00Z", "2026-01-01T09:00:00+08:00"])


def test_schema_and_json_preserve_two_element_array_contract():
    """公开 Schema 和序列化继续使用固定长度数组。"""
    schema = ADAPTER.json_schema()
    assert schema["type"] == "array"
    assert schema["minItems"] == schema["maxItems"] == 2
    assert all(item["format"] == "date-time" for item in schema["prefixItems"])
    value = ADAPTER.validate_python([START, END])
    assert json.loads(ADAPTER.dump_json(value)) == [START, END]


@pytest.mark.parametrize("model", [UserPageReqVO, UserExportReqVO])
def test_optional_ranges_and_assignment_share_validation(model):
    """未提供与显式空值表示不筛选，空数组与非法赋值均拒绝。"""
    assert model().create_time is None
    assert model(createTime=None).create_time is None
    with pytest.raises(ValidationError):
        model(createTime=[])
    request = model(createTime=[START, END])
    with pytest.raises(ValidationError):
        request.create_time = [END, START]
    assert request.create_time == (datetime(2026, 1, 1), datetime(2026, 1, 2))


@pytest.mark.parametrize("module_name,class_name,field_name", RANGE_REQUESTS)
def test_all_request_ranges_bind_repeated_query_parameters(module_name, class_name, field_name):
    """逐个真实 VO 验证可空范围仍完整收集重复参数，不会只取最后一项。"""
    model = getattr(importlib.import_module(module_name), class_name)
    alias = model.model_fields[field_name].alias
    app = FastAPI()

    @app.get("/query")
    def query(request: model = Query()):
        return {"value": getattr(request, field_name)}

    with TestClient(app) as client:
        assert client.get("/query").json() == {"value": None}
        for name in (alias, field_name):
            response = client.get("/query", params=[(name, START), (name, END)])
            assert response.status_code == 200
            assert response.json() == {"value": [START, END]}
        invalid = client.get("/query", params=[(alias, START)])
        assert invalid.status_code == 422
        assert invalid.json()["detail"][0]["loc"] == ["query", alias, 1]
        with pytest.raises(ValidationError):
            model.model_validate({alias: []})


def test_invalid_range_uses_existing_public_validation_response():
    """范围顺序错误沿用项目的参数校验响应，不产生内部异常。"""
    app = FastAPI()
    GlobalExceptionHandler(debug=False).register(app)

    @app.get("/query")
    def query(request: UserPageReqVO = Query()):
        return request

    with TestClient(app) as client:
        response = client.get("/query", params=[("createTime", END), ("createTime", START)])
    assert response.status_code == 200
    body = response.json()
    assert body["code"] != 0
    assert body["error"]["fields"][0]["field"] == "createTime"
    assert "input" not in body["error"]["fields"][0]


def test_query_range_normalizes_encoded_offsets():
    """重复查询参数中的正偏移与 UTC 端点按同一时刻完成绑定。"""
    app = FastAPI()

    @app.get("/query")
    def query(request: UserPageReqVO = Query()):
        return {"value": request.create_time}

    with TestClient(app) as client:
        response = client.get(
            "/query",
            params=[
                ("createTime", "2026-01-01T08:00:00+08:00"),
                ("createTime", "2026-01-01T00:00:00Z"),
            ],
        )
    assert response.status_code == 200
    assert response.json() == {"value": [START, START]}


@pytest.mark.parametrize("public_first", [True, False])
def test_public_range_import_preserves_type_identity(public_first):
    """两种首次导入顺序都保留同一公共类型。"""
    backend = Path(__file__).resolve().parents[4] / "dushan-admin-backend"
    names = ["framework.common.contracts", "framework.common.contracts.datetime_range_input"]
    if not public_first:
        names.reverse()
    script = """
import importlib
import sys
sys.path.insert(0, sys.argv[1])
first, second = (importlib.import_module(name) for name in sys.argv[2:])
assert first.DateTimeRangeInput is second.DateTimeRangeInput
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(backend), *names],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
