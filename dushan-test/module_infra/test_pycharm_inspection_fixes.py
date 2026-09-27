import importlib
import inspect
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from module_infra.api.config.dto.config_item_dto import ConfigItemDTO
from module_infra.controller.admin.config.config_type_controller import ConfigTypeController
from module_infra.controller.admin.config.vo.data.data_page_req_vo import ConfigDataPageReqVO
from module_infra.controller.admin.config.vo.type.type_module_req_vo import ConfigTypeModuleReqVO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.dal.dataobject.mq.mq_do import MqDO
from module_infra.dal.mapper.config.config_type_mapper import ConfigTypeMapper
from module_infra.dal.mapper.file.file_config_mapper import FileConfigMapper
from module_infra.dal.mapper.mq.mq_definition_mapper import MqDefinitionMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.config.config_module_enum import ConfigModuleEnum
from module_infra.service.config.config_data_service_impl import ConfigDataServiceImpl
from module_infra.service.data_source.data_source_config_service_impl import (
    DataSourceConfigServiceImpl,
)
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.mapper.dept.post_mapper import PostMapper

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("sort", [0, -1, 7])
def test_configuration_sort_is_an_integer_not_an_identifier(sort):
    item = ConfigItemDTO(id=101, name="测试配置", config_key="key", sort=sort)
    assert item.id == "101"
    assert item.sort == sort
    assert type(item.model_dump(mode="json")["sort"]) is int


async def test_duplicate_data_source_name_keeps_business_error():
    service = DataSourceConfigServiceImpl()
    service.data_source_config_mapper = SimpleNamespace(
        select_by_name=AsyncMock(return_value=SimpleNamespace(id=12))
    )
    with pytest.raises(ServiceException) as caught:
        await service._validate_data_source_config_name_unique(None, "重复配置")
    assert caught.value.error_code is ErrorCodeConstants.DATA_SOURCE_CONFIG_NAME_DUPLICATE
    assert "重复配置" in str(caught.value)


@pytest.mark.parametrize(
    "method", ["get_config_page_with_type_name", "get_config_list_with_type_name"]
)
async def test_config_data_filter_passes_module_code_to_string_service(method):
    service = ConfigDataServiceImpl()
    lookup = AsyncMock(return_value=[])
    service.config_type_service = SimpleNamespace(get_config_types_by_module=lookup)
    service.config_data_mapper = SimpleNamespace(
        select_page=AsyncMock(return_value=PageResult.empty())
    )
    await getattr(service, method)(ConfigDataPageReqVO(module=ConfigModuleEnum.INFRA))
    lookup.assert_awaited_once_with("infra")


async def test_config_type_controller_passes_module_code_to_string_service():
    lookup = AsyncMock(return_value=[])
    service = SimpleNamespace(get_config_types_by_module=lookup)
    await ConfigTypeController.get_simple_config_type_list(
        ConfigTypeModuleReqVO(module=ConfigModuleEnum.INFRA), service
    )
    lookup.assert_awaited_once_with("infra")


@pytest.fixture
def mapper_session():
    engine = create_engine("sqlite://")
    models = (InfraConfigTypeDO, FileConfigDO, MqDO, PostDO)
    for model in models:
        model.__table__.create(engine)
    audit = dict(create_time=datetime(2026, 1, 1), update_time=datetime(2026, 1, 1))
    with Session(engine) as session:
        session.add_all(
            [
                InfraConfigTypeDO(
                    id=1, tenant_id="unit", module="infra", name="启用", code="a", status=1, **audit
                ),
                InfraConfigTypeDO(
                    id=2, tenant_id="unit", module="infra", name="停用", code="b", status=0, **audit
                ),
                InfraConfigTypeDO(
                    id=3,
                    tenant_id="unit",
                    module="system",
                    name="其他",
                    code="c",
                    status=1,
                    **audit,
                ),
                FileConfigDO(
                    id=11, tenant_id="unit", name="一", storage=1, config={}, status=1, **audit
                ),
                FileConfigDO(
                    id=12, tenant_id="unit", name="停用", storage=1, config={}, status=0, **audit
                ),
                FileConfigDO(
                    id=13, tenant_id="unit", name="三", storage=1, config={}, status=1, **audit
                ),
                MqDO(id=31, topic="a", consumer="x", **audit),
                MqDO(id=32, topic="a", consumer="y", **audit),
                MqDO(id=33, topic="b", consumer="z", **audit),
                PostDO(id=21, tenant_id="unit", name="一", code="p1", sort=0, status=1, **audit),
                PostDO(id=22, tenant_id="unit", name="停用", code="p2", sort=0, status=0, **audit),
                PostDO(id=23, tenant_id="unit", name="三", code="p3", sort=0, status=1, **audit),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


async def test_module_configuration_query_selects_enabled_rows(mapper_session):
    mapper = ConfigTypeMapper()
    mapper.read = AsyncMock(side_effect=mapper_session.execute)
    rows = await mapper.select_list_by_module("infra")
    assert [row.id for row in rows] == [1]


async def test_generic_mapper_conditions_remain_available(mapper_session):
    mapper = ConfigTypeMapper()
    mapper.read = AsyncMock(side_effect=mapper_session.execute)
    rows = await mapper.select_list(InfraConfigTypeDO.status == StatusEnum.DISABLE.code)
    assert [row.id for row in rows] == [2]


async def test_file_configuration_business_filter_preserves_order(mapper_session):
    mapper = FileConfigMapper()
    mapper.read = AsyncMock(side_effect=mapper_session.execute)
    assert [row.id for row in await mapper.select_enabled_list()] == [13, 11]


async def test_mq_business_filter_preserves_topic_and_consumer(mapper_session):
    mapper = MqDefinitionMapper()
    mapper.read = AsyncMock(side_effect=mapper_session.execute)
    assert [row.id for row in await mapper.select_filtered_list(topic="a")] == [32, 31]
    assert [row.id for row in await mapper.select_filtered_list(topic="a", consumer="x")] == [31]


async def test_post_business_filter_preserves_ids_and_status(mapper_session):
    mapper = PostMapper()
    mapper.read = AsyncMock(side_effect=mapper_session.execute)
    rows = await mapper.select_filtered_list(ids=[21, 22], statuses=[1])
    assert [row.id for row in rows] == [21]


@pytest.mark.parametrize(
    "interface_path,implementation_path,methods",
    [
        (
            "module_infra.service.file.file_config_service.FileConfigService",
            "module_infra.service.file.file_config_service_impl.FileConfigServiceImpl",
            (
                "create_file_config",
                "update_file_config",
                "update_file_config_master",
                "delete_file_config",
                "get_file_config",
                "get_file_config_page",
                "test_file_config",
            ),
        ),
        (
            "module_infra.service.job.job_service.JobService",
            "module_infra.service.job.job_service_impl.JobServiceImpl",
            ("create_job", "update_job", "get_job_page"),
        ),
        (
            "module_infra.service.job.job_log_service.JobLogService",
            "module_infra.service.job.job_log_service_impl.JobLogServiceImpl",
            ("get_job_log",),
        ),
        (
            "module_infra.service.logger.api_access_log_service.ApiAccessLogService",
            "module_infra.service.logger.api_access_log_service_impl.ApiAccessLogServiceImpl",
            ("create_api_access_log",),
        ),
        (
            "module_infra.service.logger.api_error_log_service.ApiErrorLogService",
            "module_infra.service.logger.api_error_log_service_impl.ApiErrorLogServiceImpl",
            ("create_api_error_log",),
        ),
        (
            "module_infra.service.online.online_service.OnlineService",
            "module_infra.service.online.online_service_impl.OnlineServiceImpl",
            ("get_online_list", "force_logout"),
        ),
        (
            "framework.starter_security.spi.tenant_access_provider.TenantAccessProvider",
            "framework.starter_tenant.core.tenant_service.TenantService",
            ("enter",),
        ),
        (
            "module_system.framework.sms.client.sms_client.SmsClient",
            "module_system.framework.sms.client.providers.huawei_sms_client.HuaweiSmsClient",
            ("parse_sms_receive_status",),
        ),
        (
            "module_system.service.tenant.handler.tenant_menu_handler.TenantMenuHandler",
            "module_system.service.tenant.handler.menu_filter_handler.MenuListFilterHandler",
            ("handle",),
        ),
    ],
)
def test_implementations_accept_declared_keyword_arguments(
    interface_path, implementation_path, methods
):
    interface_module, _, interface_name = interface_path.rpartition(".")
    implementation_module, _, implementation_name = implementation_path.rpartition(".")
    interface = getattr(importlib.import_module(interface_module), interface_name)
    implementation = getattr(importlib.import_module(implementation_module), implementation_name)
    for name in methods:
        declared = inspect.signature(getattr(interface, name))
        keywords = {key: object() for key in declared.parameters if key != "self"}
        inspect.signature(getattr(implementation, name)).bind(object(), **keywords)
