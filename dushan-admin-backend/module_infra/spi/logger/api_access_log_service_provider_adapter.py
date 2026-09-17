from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject
from module_infra.service.logger.api_access_log_service import ApiAccessLogService
from module_infra.spi.logger.dto.api_access_log_create_req_dto import ApiAccessLogCreateReqDTO


@framework
class ApiAccessLogServiceProviderAdapter:
    service: ApiAccessLogService = Inject()

    async def write(self, values):
        await self.service.create_api_access_log(ApiAccessLogCreateReqDTO.model_validate(values))
