from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from module_infra.controller.admin.codegen.vo.codegen_update_req_vo import CodegenUpdateReqVO
from module_infra.controller.admin.config.vo.type.config_type_save_req_vo import ConfigTypeSaveReqVO
from module_infra.controller.admin.file.vo.config.file_config_save_req_vo import FileConfigSaveReqVO
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.dal.dataobject.config.infra_config_type_do import InfraConfigTypeDO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.service.codegen.codegen_service_impl import CodegenServiceImpl
from module_infra.service.config.config_data_service_impl import ConfigDataServiceImpl
from module_infra.service.config.config_type_service_impl import ConfigTypeServiceImpl
from module_infra.service.file.file_config_service_impl import FileConfigServiceImpl

pytestmark = pytest.mark.unit


async def test_required_config_type_returns_entity_and_rejects_absent_type():
    row = InfraConfigTypeDO(id=1, status=StatusEnum.ENABLE.code)
    service = ConfigTypeServiceImpl()
    service.config_type_mapper = SimpleNamespace(select_by_id=AsyncMock(return_value=row))
    assert await service._validate_config_type_exists(1) is row

    service.config_type_mapper.select_by_id.return_value = None
    with pytest.raises(ServiceException):
        await service._validate_config_type_exists(1)
    request = ConfigTypeSaveReqVO(name="配置类型", code="settings", status=StatusEnum.ENABLE.code)
    with pytest.raises(ServiceException):
        await service.update_config_type(request)
    service.config_type_mapper.select_by_id.assert_awaited_with(None)


async def test_config_data_type_validation_returns_entity_and_keeps_status_check():
    row = InfraConfigTypeDO(id=1, status=StatusEnum.ENABLE.code)
    service = ConfigDataServiceImpl()
    service.config_type_service = SimpleNamespace(get_config_type_by_id=AsyncMock(return_value=row))
    assert await service._validate_config_type_exists(1) is row
    row.status = StatusEnum.DISABLE.code
    with pytest.raises(ServiceException):
        await service._validate_config_type_exists(1)
    service.config_type_service.get_config_type_by_id.return_value = None
    with pytest.raises(ServiceException):
        await service._validate_config_type_exists(1)


async def test_codegen_patch_preserves_omissions_clears_null_and_protects_schema_fields():
    table = CodegenTableDO(id=1, author="保留作者", remark="旧备注", table_comment="保留描述")
    column = CodegenColumnDO(
        id=2,
        table_id=1,
        column_name="existing_name",
        data_type="varchar",
        order_no=3,
        primary_key=False,
        field_type="str",
        dict_type="old_dictionary",
        example="保留示例",
    )
    service = CodegenServiceImpl()
    service.codegen_table_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=table), update_by_id=AsyncMock()
    )
    service.codegen_column_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=column), update_by_id=AsyncMock()
    )
    request = CodegenUpdateReqVO.model_validate(
        {
            "table": {
                "id": "1",
                "dataSourceConfigId": "7",
                "tableName": "example",
                "className": "Example",
                "remark": None,
                "createTime": "2026-01-01T00:00:00",
            },
            "columns": [
                {
                    "id": "2",
                    "tableId": "1",
                    "columnName": "must_not_replace",
                    "dataType": "bigint",
                    "orderNo": 99,
                    "primaryKey": True,
                    "dictType": None,
                }
            ],
        }
    )
    await CodegenServiceImpl.update_codegen_table.__wrapped__(service, request)
    assert table.author == "保留作者" and table.table_comment == "保留描述"
    assert table.remark is None and table.create_time is None
    assert table.data_source_config_id == 7
    assert column.dict_type is None and column.example == "保留示例"
    assert (column.column_name, column.data_type, column.order_no, column.primary_key) == (
        "existing_name",
        "varchar",
        3,
        False,
    )
    service.codegen_table_mapper.update_by_id.assert_awaited_once_with(table)
    service.codegen_column_mapper.update_by_id.assert_awaited_once_with(column)


@pytest.mark.parametrize("secret", ["omitted", None, "", "******", "[REDACTED]", "new-secret"])
@pytest.mark.parametrize("submit_remark", [False, True])
async def test_file_config_complete_save_preserves_secrets_and_clears_remark(secret, submit_remark):
    config = {
        "endpoint": "s3.us-east-1.amazonaws.com",
        "bucket": "test-bucket",
        "access_key": "key",
        "access_secret": "old-secret",
        "region": "us-east-1",
        "domain": "https://files.example.test",
    }
    old = FileConfigDO(id=1, name="old", storage=20, config=config, remark="旧备注")
    service = FileConfigServiceImpl()
    service.mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=old), update_by_id=AsyncMock()
    )
    service.database = SimpleNamespace(after_commit=Mock())
    submitted_config = {
        key: value for key, value in config.items() if key not in {"access_key", "access_secret"}
    }
    if secret != "omitted":
        submitted_config["accessSecret"] = secret
    values = {"id": "1", "name": "new", "storage": 20, "config": submitted_config}
    if submit_remark:
        values["remark"] = None
    request = FileConfigSaveReqVO.model_validate(values)
    await FileConfigServiceImpl.update_file_config.__wrapped__(service, request)
    written = service.mapper.update_by_id.await_args.args[0]
    assert (written.id, written.name, written.storage, written.remark) == (1, "new", 20, None)
    assert written.config["access_key"] == "key"
    assert written.config["access_secret"] == (
        "new-secret" if secret == "new-secret" else "old-secret"
    )
    service.database.after_commit.assert_called_once()
