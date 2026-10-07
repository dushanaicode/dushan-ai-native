from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from module_infra.api.config.config_api import ConfigApi
from module_infra.api.config.config_api_impl import ConfigApiImpl
from module_infra.api.config.dto.config_group_dto import ConfigGroupDTO
from module_infra.api.config.dto.config_item_dto import ConfigItemDTO
from module_infra.service.config.config_data_service_impl import ConfigDataServiceImpl

pytestmark = pytest.mark.unit


class TestConfigApiContracts:
    def test_runtime_protocol_accepts_implementation(self):
        assert isinstance(ConfigApiImpl(), ConfigApi)
        assert not isinstance(object(), ConfigApi)

    def test_item_identifier_stays_integer_in_internal_payload(self):
        item = ConfigItemDTO(id=9007199254740993, name="测试配置", config_key="key")

        assert type(item.id) is int
        assert item.model_dump(mode="json")["id"] == 9007199254740993

    def test_group_identifier_stays_integer_in_internal_payload(self):
        group = ConfigGroupDTO(type_id=9007199254740995, type_name="配置组", type_code="group")

        assert type(group.type_id) is int
        assert group.model_dump(mode="json")["type_id"] == 9007199254740995

    async def test_grouped_configuration_preserves_database_identifiers(self):
        service = ConfigDataServiceImpl()
        service.config_type_service = SimpleNamespace(
            get_config_types_by_module=AsyncMock(
                return_value=[SimpleNamespace(id=201, name="配置组", code="group")]
            )
        )
        service.config_data_mapper = SimpleNamespace(
            select_list_by_type_ids=AsyncMock(
                return_value=[
                    SimpleNamespace(
                        id=101,
                        type_id=201,
                        name="测试配置",
                        key="key",
                        description=None,
                        input_type="input",
                        input_props=None,
                        value="value",
                        sort=0,
                    )
                ]
            )
        )
        api = ConfigApiImpl()
        api.config_data_service = service

        groups = await api.get_grouped_configs("infra")

        assert groups[0].type_id == 201
        assert groups[0].items[0].id == 101
        service.config_data_mapper.select_list_by_type_ids.assert_awaited_once_with([201])
