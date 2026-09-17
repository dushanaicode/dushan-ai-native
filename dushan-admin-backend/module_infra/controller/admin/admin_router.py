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
admin_router.include_router(config_data_controller, tags=["Infra - 参数配置"])
admin_router.include_router(config_type_controller, tags=["Infra - 配置类型"])
admin_router.include_router(file_config_controller, tags=["Infra - 文件配置"])
admin_router.include_router(file_controller, tags=["Infra - 文件存储"])
admin_router.include_router(job_controller, tags=["Infra - 定时任务"])
admin_router.include_router(job_log_controller, tags=["Infra - 定时任务日志"])
admin_router.include_router(api_access_log_controller, tags=["Infra - API 访问日志"])
admin_router.include_router(api_error_log_controller, tags=["Infra - API 错误日志"])
admin_router.include_router(online_controller, tags=["Infra - 在线用户管理"])
admin_router.include_router(cache_monitor_controller, tags=["Infra - 缓存监控"])
admin_router.include_router(cache_controller, tags=["Infra - 缓存管理"])
admin_router.include_router(server_controller, tags=["Infra - 服务器信息管理"])
admin_router.include_router(data_source_config_controller, tags=["Infra - 数据源配置"])
admin_router.include_router(mq_controller, tags=["Infra - MQ 管理"])
admin_router.include_router(mq_log_controller, tags=["Infra - MQ 消费日志"])
admin_router.include_router(websocket_controller_router, tags=["Infra - WebSocket 管理"])
admin_router.include_router(codegen_controller, tags=["Infra - 代码生成"])
