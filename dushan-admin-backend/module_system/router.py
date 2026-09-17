from fastapi import APIRouter

from module_system.controller.admin.admin_router import admin_router

admin_router_main = APIRouter(prefix="/admin-api/system")
admin_router_main.include_router(admin_router)
routers = [admin_router_main]
