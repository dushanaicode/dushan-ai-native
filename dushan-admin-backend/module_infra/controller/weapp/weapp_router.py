from fastapi import APIRouter

from module_infra.controller.weapp.file.file_weapp_file_controller import weapp_file_controller

# 创建WeApp端二级路由器
weapp_router = APIRouter()

# 包含三级路由（控制器）
weapp_router.include_router(weapp_file_controller, tags=["Infra WeApp - 文件存储"])
