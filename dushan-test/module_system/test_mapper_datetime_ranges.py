from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.sql import operators, visitors
from sqlalchemy.sql.elements import BinaryExpression

from framework.starter_database.ddl.ddl_cli import DdlCli
from module_infra.dal.mapper.codegen.codegen_table_mapper import CodegenTableMapper
from module_infra.dal.mapper.config.config_data_mapper import ConfigDataMapper
from module_infra.dal.mapper.config.config_type_mapper import ConfigTypeMapper
from module_infra.dal.mapper.data_source.data_source_config_mapper import DataSourceConfigMapper
from module_infra.dal.mapper.file.file_config_mapper import FileConfigMapper
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.dal.mapper.job.job_mapper import JobMapper
from module_infra.dal.mapper.logger.api_access_log_mapper import ApiAccessLogMapper
from module_infra.dal.mapper.logger.api_error_log_mapper import ApiErrorLogMapper
from module_infra.dal.mapper.mq.mq_definition_mapper import MqDefinitionMapper
from module_system.dal.mapper.announcement.announcement_mapper import AnnouncementMapper
from module_system.dal.mapper.dept.post_mapper import PostMapper
from module_system.dal.mapper.dict.dict_data_mapper import DictDataMapper
from module_system.dal.mapper.dict.dict_type_mapper import DictTypeMapper
from module_system.dal.mapper.logger.login_log_mapper import LoginLogMapper
from module_system.dal.mapper.logger.operate_log_mapper import OperateLogMapper
from module_system.dal.mapper.mail.mail_template_mapper import MailTemplateMapper
from module_system.dal.mapper.notification.notice_log_mapper import NoticeLogMapper
from module_system.dal.mapper.notification.notice_mapper import NoticeMapper
from module_system.dal.mapper.notification.notice_message_mapper import NoticeMessageMapper
from module_system.dal.mapper.oauth2.oauth2_access_token_mapper import OAuth2AccessTokenMapper
from module_system.dal.mapper.oauth2.oauth2_client_mapper import OAuth2ClientMapper
from module_system.dal.mapper.permission.role_mapper import RoleMapper
from module_system.dal.mapper.sms.sms_channel_mapper import SmsChannelMapper
from module_system.dal.mapper.sms.sms_log_mapper import SmsLogMapper
from module_system.dal.mapper.sms.sms_template_mapper import SmsTemplateMapper
from module_system.dal.mapper.social.social_client_mapper import SocialClientMapper
from module_system.dal.mapper.social.social_user_mapper import SocialUserMapper
from module_system.dal.mapper.tenant.tenant_mapper import TenantMapper
from module_system.dal.mapper.tenant.tenant_package_mapper import TenantPackageMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit

MAPPER_RANGES = [
    (AnnouncementMapper, "select_page", "create_time", "create_time"),
    (PostMapper, "select_page", "create_time", "create_time"),
    (DictDataMapper, "select_page", "create_time", "create_time"),
    (DictTypeMapper, "select_page", "create_time", "create_time"),
    (LoginLogMapper, "select_page", "create_time", "create_time"),
    (OperateLogMapper, "select_page_vo", "create_time", "create_time"),
    (MailTemplateMapper, "select_page", "create_time", "create_time"),
    (NoticeLogMapper, "select_page", "create_time", "create_time"),
    (NoticeMapper, "select_page", "create_time", "create_time"),
    (NoticeMessageMapper, "select_page", "create_time", "create_time"),
    (NoticeMessageMapper, "select_page_my", "create_time", "create_time"),
    (OAuth2AccessTokenMapper, "select_page", "create_time", "create_time"),
    (OAuth2ClientMapper, "select_page", "create_time", "create_time"),
    (RoleMapper, "select_page", "create_time", "create_time"),
    (SmsChannelMapper, "select_page", "create_time", "create_time"),
    (SmsLogMapper, "select_page", "send_time", "send_time"),
    (SmsLogMapper, "select_page", "receive_time", "receive_time"),
    (SmsTemplateMapper, "select_page", "create_time", "create_time"),
    (SocialClientMapper, "select_page", "create_time", "create_time"),
    (SocialUserMapper, "select_page", "create_time", "create_time"),
    (TenantMapper, "select_page", "create_time", "create_time"),
    (TenantPackageMapper, "select_page", "create_time", "create_time"),
    (AdminUserMapper, "select_page", "create_time", "create_time"),
    (CodegenTableMapper, "select_page", "create_time", "create_time"),
    (ConfigDataMapper, "select_page", "create_time", "create_time"),
    (ConfigTypeMapper, "select_page", "create_time", "create_time"),
    (DataSourceConfigMapper, "select_page", "create_time", "create_time"),
    (FileConfigMapper, "select_page", "create_time", "create_time"),
    (FileMapper, "select_page", "create_time", "create_time"),
    (JobMapper, "select_page", "create_time", "create_time"),
    (ApiAccessLogMapper, "select_page", "begin_time", "begin_time"),
    (ApiErrorLogMapper, "select_page", "exception_time", "exception_time"),
    (MqDefinitionMapper, "select_page", "create_time", "create_time"),
]


async def capture_query(mapper_type, method_name, values):
    """调用真实 VO 和 Mapper，在已有分页边界截获语句，不访问数据库。"""
    mapper = mapper_type()
    method = getattr(mapper, method_name)
    request_type = method.__globals__[method.__annotations__["req_vo"]]
    request = request_type.model_validate(values)
    page = object()
    mapper.paginate_query = AsyncMock(return_value=page)
    arguments = {}
    if mapper_type is AdminUserMapper:
        arguments = {"dept_ids": None, "user_ids": None}
    elif mapper_type is JobMapper:
        arguments = {"tenant_id": "7", "include_global": False}
    elif method_name == "select_page_my":
        arguments = {"user_id": 19, "user_type": 2}

    assert await method(request, **arguments) is page

    mapper.paginate_query.assert_awaited_once()
    statement, actual_request = mapper.paginate_query.await_args.args
    assert actual_request is request
    return mapper.model, statement


def range_expressions(statement):
    """取得查询中的 BETWEEN 表达式供列名和端点断言使用。"""
    return [
        expression
        for expression in visitors.iterate(statement)
        if isinstance(expression, BinaryExpression) and expression.operator is operators.between_op
    ]


@pytest.mark.parametrize(
    "mapper_type,method_name,field_name,column_name",
    MAPPER_RANGES,
    ids=[
        f"{mapper_type.__name__}-{method_name}-{field_name}"
        for mapper_type, method_name, field_name, _ in MAPPER_RANGES
    ],
)
@pytest.mark.parametrize(
    "include_field,bounds,expected",
    [
        pytest.param(False, None, None, id="missing"),
        pytest.param(True, None, None, id="null"),
        pytest.param(
            True,
            ["2026-10-06 04:00:00", "2026-10-06 09:00:00"],
            (datetime(2026, 10, 6, 4), datetime(2026, 10, 6, 9)),
            id="naive-range",
        ),
        pytest.param(
            True,
            ["2026-10-06T12:00:00+08:00", "2026-10-06T09:00:00Z"],
            (datetime(2026, 10, 6, 4), datetime(2026, 10, 6, 9)),
            id="utc-range",
        ),
        pytest.param(
            True,
            ["2026-10-06T12:00:00+08:00", "2026-10-06T04:00:00Z"],
            (datetime(2026, 10, 6, 4), datetime(2026, 10, 6, 4)),
            id="same-instant",
        ),
    ],
)
async def test_mapper_datetime_range_query(
    mapper_type, method_name, field_name, column_name, include_field, bounds, expected
):
    """所有日期范围均按正确列生成 UTC 闭区间，省略或空值不追加范围条件。"""
    values = {field_name: bounds} if include_field else {}
    model, statement = await capture_query(mapper_type, method_name, values)

    ranges = range_expressions(statement)
    if expected is None:
        assert ranges == []
    else:
        (expression,) = ranges
        assert expression.left.compare(getattr(model, column_name).__clause_element__())
        assert tuple(bound.value for bound in expression.right.clauses) == expected
        assert all(bound.value.tzinfo is None for bound in expression.right.clauses)

    predicates = list(visitors.iterate(statement.whereclause))
    if method_name == "select_page_my":
        assert any(predicate.compare(model.user_id == 19) for predicate in predicates)
        assert any(predicate.compare(model.user_type == 2) for predicate in predicates)
    elif mapper_type is JobMapper:
        assert any(predicate.compare(model.tenant_id == "7") for predicate in predicates)


async def test_sms_send_and_receive_ranges_keep_separate_columns_and_endpoints():
    """短信发送和回执两个范围同时传入时，各自使用对应的列和端点。"""
    model, statement = await capture_query(
        SmsLogMapper,
        "select_page",
        {
            "send_time": ["2026-10-06T12:00:00+08:00", "2026-10-06T13:00:00+08:00"],
            "receive_time": ["2026-10-06T06:00:00Z", "2026-10-06T07:00:00Z"],
        },
    )

    expressions = range_expressions(statement)
    assert len(expressions) == 2
    expected = (
        model.send_time.between(datetime(2026, 10, 6, 4), datetime(2026, 10, 6, 5)),
        model.receive_time.between(datetime(2026, 10, 6, 6), datetime(2026, 10, 6, 7)),
    )
    assert all(
        any(expression.compare(condition) for expression in expressions) for condition in expected
    )
