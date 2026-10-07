import pytest
from fastapi import FastAPI

from module_infra.controller.admin.admin_router import admin_router as infra_admin_router
from module_infra.controller.admin.websocket.websocket_controller import websocket_controller_router
from module_system.controller.admin.admin_router import admin_router as system_admin_router


class TestAdminRouterTags:
    @pytest.mark.parametrize(
        "router",
        [system_admin_router, infra_admin_router, websocket_controller_router],
        ids=["system", "infra", "websocket"],
    )
    def test_openapi_operations_keep_one_controller_tag(self, router):
        """汇总后的每个接口保留单个标签，避免重复分类或丢失分类。"""
        app = FastAPI()
        app.include_router(router)

        operations = [
            operation for path in app.openapi()["paths"].values() for operation in path.values()
        ]

        assert operations
        assert all(len(operation["tags"]) == 1 for operation in operations)
