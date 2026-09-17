import importlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO
from module_infra.controller.admin.file.vo.config.file_config_resp_vo import FileConfigRespVO
from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.framework.file.core.client.local.local_file_client import LocalFileClient
from module_infra.framework.file.core.client.local.local_file_client_config import (
    LocalFileClientConfig,
)

ENUMS = [
    (
        "module_infra.definitions.enums.codegen.codegen_front_type_enum",
        "CodegenFrontTypeEnum",
        {
            "VUE3_VBEN5_ELE": (0, "Vue3 Vben5 Element Plus"),
            "VUE3_VBEN5_ANTD": (1, "Vue3 Vben5 Ant Design Vue"),
        },
    ),
    (
        "module_infra.definitions.enums.codegen.codegen_scene_enum",
        "CodegenSceneEnum",
        {"ADMIN": (1, "管理后台"), "APP": (2, "用户端")},
    ),
    (
        "module_infra.definitions.enums.codegen.codegen_template_type_enum",
        "CodegenTemplateTypeEnum",
        {"CRUD": (1, "基础 CRUD"), "TREE": (2, "树形 CRUD"), "SUB": (15, "主子表 CRUD")},
    ),
    (
        "module_infra.definitions.enums.config.boolean_string_enum",
        "BooleanStringEnum",
        {"YES": ("true", "是"), "NO": ("false", "否")},
    ),
    (
        "module_infra.definitions.enums.config.config_module_enum",
        "ConfigModuleEnum",
        {
            "SYSTEM": ("system", "系统"),
            "INFRA": ("infra", "基础设施"),
            "FRAMEWORK": ("framework", "框架"),
            "AI": ("ai", "AI"),
        },
    ),
    (
        "module_infra.definitions.enums.data_source.data_source_db_type_enum",
        "DataSourceDbTypeEnum",
        {
            "POSTGRESQL": ("postgresql", "PostgreSQL"),
            "MYSQL": ("mysql", "MySQL/MariaDB"),
            "SQLITE": ("sqlite", "SQLite"),
            "ORACLE": ("oracle", "Oracle"),
            "MSSQL": ("mssql", "Microsoft SQL Server"),
            "KINGBASE": ("kingbase", "人大金仓 (KingbaseES)"),
            "HIGHGO": ("highgo", "瀚高数据库 (HighGo DB)"),
            "GAUSSDB": ("gaussdb", "华为 GaussDB"),
        },
    ),
    (
        "module_infra.definitions.enums.data_source.data_source_health_status_enum",
        "DataSourceHealthStatusEnum",
        {"HEALTHY": (0, "健康"), "WARNING": (1, "警告"), "FAILURE": (2, "故障")},
    ),
    (
        "module_infra.definitions.enums.data_source.data_source_type_enum",
        "DataSourceTypeEnum",
        {"MASTER": (1, "主库"), "SLAVE": (2, "从库"), "BACKUP": (3, "备份库")},
    ),
    (
        "module_infra.definitions.enums.job.job_log_status_enum",
        "JobLogStatusEnum",
        {"RUNNING": (0, "运行中"), "SUCCESS": (1, "成功"), "FAILURE": (2, "失败")},
    ),
    (
        "module_infra.definitions.enums.job.job_status_enum",
        "JobStatusEnum",
        {"INIT": (0, "初始化中"), "NORMAL": (1, "开启"), "STOP": (2, "暂停")},
    ),
    (
        "module_infra.definitions.enums.logger.api_error_log_process_status_enum",
        "ApiErrorLogProcessStatusEnum",
        {"INIT": (0, "未处理"), "DONE": (1, "已处理"), "IGNORE": (2, "已忽略")},
    ),
    (
        "module_infra.definitions.enums.mq.mq_log_status_enum",
        "MqLogStatusEnum",
        {"CONSUMING": (0, "消费中"), "SUCCESS": (1, "消费成功"), "FAILURE": (2, "消费失败")},
    ),
]
MODELS = [
    (
        "module_infra.dal.dataobject.codegen.codegen_column_do",
        "CodegenColumnDO",
        [
            "table_id",
            "column_name",
            "column_comment",
            "data_type",
            "column_size",
            "field_type",
            "field_name",
            "create_operation",
            "update_operation",
            "list_operation",
            "list_operation_result",
            "list_operation_condition",
            "nullable",
            "html_type",
            "dict_type",
            "example",
            "order_no",
            "primary_key",
        ],
    ),
    (
        "module_infra.dal.dataobject.codegen.codegen_table_do",
        "CodegenTableDO",
        [
            "data_source_config_id",
            "table_name",
            "table_comment",
            "class_name",
            "author",
            "remark",
            "template_type",
            "front_type",
            "scene",
            "parent_menu_id",
            "module_name",
            "business_name",
            "class_comment",
            "enable_export",
            "tree_parent_column_id",
            "tree_name_column_id",
            "master_table_id",
            "sub_join_column_id",
            "sub_join_many",
        ],
    ),
    (
        "module_infra.dal.dataobject.config.config_data_do",
        "InfraConfigDataDO",
        [
            "type_id",
            "name",
            "key",
            "value",
            "description",
            "input_type",
            "input_props",
            "sort",
            "visible",
            "remark",
        ],
    ),
    (
        "module_infra.dal.dataobject.config.config_type_do",
        "InfraConfigTypeDO",
        ["module", "name", "code", "status", "remark", "deleted_time"],
    ),
    (
        "module_infra.dal.dataobject.data_source.data_source_config_do",
        "DataSourceConfigDO",
        [
            "name",
            "url",
            "status",
            "db_type",
            "source_type",
            "is_default",
            "pool_size",
            "max_overflow",
            "pool_recycle",
            "pool_timeout",
            "echo",
            "remark",
        ],
    ),
    (
        "module_infra.dal.dataobject.file.file_config_do",
        "FileConfigDO",
        ["name", "storage", "remark", "status", "master", "config"],
    ),
    (
        "module_infra.dal.dataobject.file.file_content_do",
        "FileContentDO",
        ["config_id", "path", "content"],
    ),
    (
        "module_infra.dal.dataobject.file.file_do",
        "FileDO",
        [
            "config_id",
            "name",
            "original_name",
            "path",
            "storage_path",
            "url",
            "type",
            "size",
            "hash",
            "file_metadata",
        ],
    ),
    (
        "module_infra.dal.dataobject.job.job_do",
        "JobDO",
        [
            "name",
            "status",
            "handler_name",
            "handler_param",
            "cron_expression",
            "retry_count",
            "retry_interval",
            "monitor_timeout",
        ],
    ),
    (
        "module_infra.dal.dataobject.job.job_log_do",
        "JobLogDO",
        [
            "job_id",
            "handler_name",
            "handler_param",
            "execute_index",
            "begin_time",
            "end_time",
            "duration",
            "status",
            "result",
        ],
    ),
    (
        "module_infra.dal.dataobject.logger.api_access_log_do",
        "ApiAccessLogDO",
        [
            "trace_id",
            "user_id",
            "user_type",
            "application_name",
            "request_method",
            "request_url",
            "request_params",
            "response_body",
            "user_ip",
            "user_agent",
            "operate_module",
            "operate_name",
            "operate_type",
            "begin_time",
            "end_time",
            "duration",
            "result_code",
            "result_msg",
        ],
    ),
    (
        "module_infra.dal.dataobject.logger.api_error_log_do",
        "ApiErrorLogDO",
        [
            "trace_id",
            "user_id",
            "user_type",
            "application_name",
            "request_method",
            "request_url",
            "request_params",
            "user_ip",
            "user_agent",
            "exception_time",
            "exception_name",
            "exception_message",
            "exception_root_cause_message",
            "exception_stack_trace",
            "exception_class_name",
            "exception_file_name",
            "exception_method_name",
            "exception_line_number",
            "process_status",
            "process_time",
            "process_user_id",
        ],
    ),
    (
        "module_infra.dal.dataobject.mq.mq_do",
        "MqDO",
        ["topic", "consumer", "retry_count", "description"],
    ),
    (
        "module_infra.dal.dataobject.mq.mq_log_do",
        "MqLogDO",
        [
            "message_id",
            "topic",
            "consumer",
            "execute_index",
            "begin_time",
            "end_time",
            "duration",
            "status",
            "result",
            "payload",
        ],
    ),
]
ERRORS = [
    ("JOB_NOT_EXISTS", 1001001000, "infra.job.not_exists"),
    ("JOB_HANDLER_EXISTS", 1001001001, "infra.job.handler_exists"),
    ("JOB_CHANGE_STATUS_INVALID", 1001001002, "infra.job.change_status_invalid"),
    ("JOB_CHANGE_STATUS_EQUALS", 1001001003, "infra.job.change_status_equals"),
    ("JOB_UPDATE_ONLY_NORMAL_STATUS", 1001001004, "infra.job.update_only_normal_status"),
    ("JOB_CRON_EXPRESSION_VALID", 1001001005, "infra.job.cron_expression_valid"),
    ("JOB_HANDLER_BEAN_NOT_EXISTS", 1001001006, "infra.job.handler_bean_not_exists"),
    ("JOB_HANDLER_BEAN_TYPE_ERROR", 1001001007, "infra.job.handler_bean_type_error"),
    ("JOB_UPDATE_FAIL", 1001001008, "infra.job.update_fail"),
    ("JOB_STATUS_UPDATE_FAIL", 1001001009, "infra.job.status_update_fail"),
    ("JOB_TRIGGER_FAIL", 1001001010, "infra.job.trigger_fail"),
    ("JOB_SYNC_FAIL_SCHEDULER", 1001001011, "infra.job.sync_fail_scheduler"),
    ("API_ERROR_LOG_NOT_FOUND", 1001002000, "infra.log.error_log_not_found"),
    ("API_ERROR_LOG_PROCESSED", 1001002001, "infra.log.error_log_processed"),
    ("FILE_PATH_EXISTS", 1001003000, "infra.file.path_exists"),
    ("FILE_NOT_EXISTS", 1001003001, "infra.file.not_exists"),
    ("FILE_IS_EMPTY", 1001003002, "infra.file.is_empty"),
    ("FILE_NODE_NOT_EXISTS", 1001004000, "infra.file.node_not_exists"),
    ("FILE_NODE_ALREADY_EXISTS", 1001004001, "infra.file.node_already_exists"),
    ("FILE_NODE_PARENT_NOT_EXISTS", 1001004002, "infra.file.node_parent_not_exists"),
    ("FILE_NODE_PARENT_NOT_FOLDER", 1001004003, "infra.file.node_parent_not_folder"),
    ("FILE_NODE_CANNOT_MOVE_TO_CHILD", 1001004004, "infra.file.node_cannot_move_to_child"),
    ("FILE_CONFIG_DATA_NOT_EXISTS", 1001005000, "infra.file.config_not_exists"),
    ("FILE_CONFIG_DELETE_FAIL_MASTER", 1001005001, "infra.file.config_delete_fail_master"),
    ("FILE_CONFIG_HAS_FILE", 1001005002, "infra.file.config_has_file"),
    ("CACHE_GET_MONITOR_INFO_ERROR", 1001006000, "infra.cache.get_monitor_info_error"),
    ("CACHE_DELETE_FAILED", 1001006001, "infra.cache.delete_failed"),
    ("CACHE_FLUSHDB_FAILED", 1001006002, "infra.cache.flushdb_failed"),
    ("MQ_DEFINITION_NOT_EXISTS", 1001007000, "infra.mq.definition_not_exists"),
    ("MQ_DEFINITION_TOPIC_EXISTS", 1001007001, "infra.mq.definition_topic_exists"),
    ("MQ_DEFINITION_CONSUMER_EXISTS", 1001007002, "infra.mq.definition_consumer_exists"),
    (
        "MQ_DEFINITION_CHANGE_STATUS_INVALID",
        1001007003,
        "infra.mq.definition_change_status_invalid",
    ),
    ("MQ_DEFINITION_CHANGE_STATUS_EQUALS", 1001007004, "infra.mq.definition_change_status_equals"),
    ("MQ_MESSAGE_NOT_EXISTS", 1001008000, "infra.mq.message_not_exists"),
    (
        "MQ_MESSAGE_RESEND_FAIL_STATUS_WRONG",
        1001008001,
        "infra.mq.message_resend_fail_status_wrong",
    ),
    ("DATA_SOURCE_CONFIG_DATA_NOT_EXISTS", 1001009000, "infra.data_source.not_exists"),
    ("DATA_SOURCE_CONFIG_NAME_DUPLICATE", 1001009001, "infra.data_source.name_duplicate"),
    ("DATA_SOURCE_CONFIG_TEST_FAILED", 1001009002, "infra.data_source.test_failed"),
    ("DATA_SOURCE_CONFIG_DELETE_DEFAULT", 1001009003, "infra.data_source.delete_default"),
    ("DATA_SOURCE_CONFIG_ACTIVATE_FAILED", 1001009004, "infra.data_source.activate_failed"),
    ("CONFIG_DATA_NOT_EXISTS", 1001010000, "infra.config.data_not_exists"),
    ("CONFIG_DATA_KEY_DUPLICATE", 1001010001, "infra.config.data_key_duplicate"),
    (
        "CONFIG_DATA_CAN_NOT_DELETE_SYSTEM_TYPE",
        1001010002,
        "infra.config.can_not_delete_system_type",
    ),
    (
        "CONFIG_DATA_GET_VALUE_ERROR_IF_VISIBLE",
        1001010003,
        "infra.config.get_value_error_if_visible",
    ),
    ("CONFIG_TYPE_NOT_EXISTS", 1001010004, "infra.config.type_not_exists"),
    ("CONFIG_TYPE_NAME_DUPLICATE", 1001010005, "infra.config.type_name_duplicate"),
    ("CONFIG_TYPE_CODE_DUPLICATE", 1001010006, "infra.config.type_code_duplicate"),
    ("CONFIG_TYPE_HAS_CHILDREN", 1001010007, "infra.config.type_has_children"),
    ("CONFIG_TYPE_NOT_ENABLE", 1001010008, "infra.config.type_not_enable"),
    ("CODEGEN_TABLE_NOT_EXISTS", 1001011000, "infra.codegen.table_not_exists"),
    ("CODEGEN_IMPORT_TABLE_EXISTS", 1001011001, "infra.codegen.import_table_exists"),
    ("CODEGEN_COLUMN_NOT_EXISTS", 1001011002, "infra.codegen.column_not_exists"),
    ("CODEGEN_SYNC_NONE_CHANGE", 1001011003, "infra.codegen.sync_none_change"),
    ("CODEGEN_IMPORT_COLUMNS_NULL", 1001011004, "infra.codegen.import_columns_null"),
    ("CODEGEN_TABLE_INFO_TABLE_COMMENT_IS_NULL", 1001011005, "infra.codegen.table_comment_is_null"),
    ("CODEGEN_SYNC_COLUMNS_NULL", 1001011006, "infra.codegen.sync_columns_null"),
]


@pytest.mark.parametrize("module,name,members", ENUMS)
def test_enum_members(module, name, members):
    target = getattr(importlib.import_module(module), name)
    assert {entry.name: (entry.code, entry.label) for entry in target} == members


@pytest.mark.parametrize("module,name,fields", MODELS)
def test_source_fields_and_tenant_contract(module, name, fields):
    target = getattr(importlib.import_module(module), name)
    assert set(fields) <= set(target.__table__.c.keys())
    if issubclass(target, TenantBaseDO):
        assert target.__table__.c.tenant_id.type.python_type is str


@pytest.mark.parametrize("name,code,key", ERRORS)
def test_error_codes_and_translations(name, code, key):
    error = getattr(ErrorCodeConstants, name)
    assert error.code == code and error.message_key == key
    root = (
        Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra/definitions/i18n"
    )
    for path in root.glob("*.json"):
        values = json.loads(path.read_text(encoding="utf-8"))
        current = values
        for segment in key.split("."):
            current = current[segment]
        assert current


def test_file_ids_reject_numbers():
    values = dict(
        configId="1",
        name="test",
        path="test.txt",
        url="http://testserver/test.txt",
        type="text/plain",
        size=1,
    )
    assert FileCreateReqVO.model_validate(values).config_id == 1
    with pytest.raises(ValidationError):
        FileCreateReqVO.model_validate({**values, "configId": 1})


@pytest.mark.parametrize(
    "value",
    [
        "../secret",
        "a/../../secret",
        "/absolute",
        "C:/secret",
        "a\\..\\secret",
        "a:stream",
        "a/./b",
        "\x00",
    ],
)
def test_storage_rejects_paths_outside_root(value):
    with pytest.raises(ValueError):
        AbstractFileClient.key(value)


@pytest.mark.asyncio
async def test_local_storage_lifecycle_and_missing_file(tmp_path):
    client = LocalFileClient(
        1, LocalFileClientConfig(base_path=str(tmp_path / "storage"), domain="http://testserver")
    )
    await client.init()
    await client.upload("directory/", b"", None)
    url = await client.upload("directory/file name.txt", b"content", "text/plain")
    assert "%20" in url
    assert await client.get_content("directory/file name.txt") == b"content"
    assert len((await client.list_objects("directory/"))["files"]) == 1
    await client.rename("directory/file name.txt", "directory/new.txt")
    await client.delete("directory/new.txt")
    with pytest.raises(FileNotFoundError):
        await client.get_content("directory/new.txt")
    await client.delete("directory/")
    await client.close()


def test_file_configuration_never_returns_credentials():
    from datetime import datetime

    value = FileConfigRespVO(
        id=1,
        name="Test",
        storage=20,
        master=False,
        config={
            "access_key": "secret-id",
            "access_secret": "secret-value",
            "endpoint": "example.com",
        },
        create_time=datetime(2026, 1, 1),
    )
    assert "secret" not in value.model_dump_json()
    assert value.config["access_secret"] == "secret-value"
