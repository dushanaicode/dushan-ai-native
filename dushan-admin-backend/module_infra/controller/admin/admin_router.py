from fastapi import APIRouter

from module_infra.controller.admin.cache.cache_controller import cache_controller
from module_infra.controller.admin.cache.cache_monitor_controller import cache_monitor_controller
from module_infra.controller.admin.codegen.codegen_controller import codegen_controller
from module_infra.controller.admin.config.config_data_controller import config_data_controller
from module_infra.controller.admin.config.config_type_controller import config_type_controller
from module_infra.controller.admin.data_source.data_source_config_controller import (
    data_source_config_controller,
)
from module_infra.controller.admin.file.file_config_controller import file_config_controller
from module_infra.controller.admin.file.file_controller import file_controller
from module_infra.controller.admin.job.job_controller import job_controller
from module_infra.controller.admin.job.job_log_controller import job_log_controller
from module_infra.controller.admin.logger.api_access_log_controller import (
    api_access_log_controller,
)
from module_infra.controller.admin.logger.api_error_log_controller import (
    api_error_log_controller,
)
from module_infra.controller.admin.mq.mq_controller import mq_controller
from module_infra.controller.admin.mq.mq_log_controller import mq_log_controller
from module_infra.controller.admin.online.online_controller import online_controller
from module_infra.controller.admin.server.server_controller import server_controller
from module_infra.controller.admin.websocket.websocket_controller import websocket_controller_router

# 创建Admin端二级路由器
admin_router = APIRouter()

# 包含三级路由（控制器）
admin_router.include_router(config_data_controller)
admin_router.include_router(config_type_controller)
admin_router.include_router(file_config_controller)
admin_router.include_router(file_controller)
admin_router.include_router(job_controller)
admin_router.include_router(job_log_controller)
admin_router.include_router(api_access_log_controller)
admin_router.include_router(api_error_log_controller)
admin_router.include_router(online_controller)
admin_router.include_router(cache_monitor_controller)
admin_router.include_router(cache_controller)
admin_router.include_router(server_controller)
admin_router.include_router(data_source_config_controller)
admin_router.include_router(mq_controller)
admin_router.include_router(mq_log_controller)
admin_router.include_router(websocket_controller_router)
admin_router.include_router(codegen_controller)
