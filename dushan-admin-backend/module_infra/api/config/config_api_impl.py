from typing import override

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_infra.api.config.config_api import ConfigApi
from module_infra.api.config.dto.config_group_dto import ConfigGroupDTO
from module_infra.service.config.config_data_service import ConfigDataService


@service(interface=ConfigApi)
class ConfigApiImpl(ConfigApi):
    """适配器：暴露 ConfigDataService 模块级配置能力给框架层"""

    config_data_service: ConfigDataService = Inject()

    @override
    async def get_value(self, module: str, key: str) -> str | None:
        return await self.config_data_service.get_value_by_module(module, key)

    @override
    async def get_values_by_type(self, module: str, type_code: str) -> dict[str, str]:
        return await self.config_data_service.get_values_by_type_code(module, type_code)

    @override
    async def get_all_by_module(self, module: str) -> dict[str, str]:
        return await self.config_data_service.get_all_by_module(module)

    @override
    async def get_grouped_configs(self, module: str) -> list[ConfigGroupDTO]:
        return await self.config_data_service.get_grouped_by_module(module)

    @override
    async def update_value(self, module: str, key: str, value: str) -> None:
        await self.config_data_service.update_value_by_module(module, key, value)

    @override
    async def batch_update_values(self, module: str, items: list[tuple[str, str]]) -> None:
        await self.config_data_service.batch_update_values_by_module(module, items)
