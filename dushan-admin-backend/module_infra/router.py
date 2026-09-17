from fastapi import APIRouter

from module_infra.controller.admin.admin_router import admin_router
from module_infra.controller.weapp.weapp_router import weapp_router

# 创建各端路由器，设置前缀
admin_router_main = APIRouter(prefix="/admin-api/infra")
weapp_router_main = APIRouter(prefix="/weapp-api/infra")

# 包含二级路由
admin_router_main.include_router(admin_router)
weapp_router_main.include_router(weapp_router)

# 导出所有路由
routers = [
    admin_router_main,
    weapp_router_main,
]
