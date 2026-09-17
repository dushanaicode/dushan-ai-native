from framework.common.enums.status_enum import StatusEnum
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from module_system.service.dict.dict_data_service import DictDataService


@service(interface=DictDataProvider)
class DictDataProviderAdapter(DictDataProvider):
    delegate: DictDataService = Inject()

    async def items(self, dict_type: str):
        entries = await self.delegate.get_dict_data_list_by_dict_type(dict_type)
        enabled = [entry for entry in entries if entry.status == StatusEnum.ENABLE.code]
        values = {str(entry.value): entry.label for entry in enabled}
        if len(values) != len(enabled) or len(set(values.values())) != len(values):
            raise ValueError("字典编码或标签重复")
        return values
