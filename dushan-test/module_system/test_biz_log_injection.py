import pytest

from framework.starter_di.public import ApplicationContext
from framework.starter_security.public import BizLogService
from module_system.service.permission.role_service import RoleService
from module_system.service.user.admin_user_service import AdminUserService
from server.bootstrap.bootstrap_step_spec import APP_BOOTSTRAP_STEPS
from server.starter_server import StarterServer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("bizlog_enabled", [True, False])
async def test_role_and_user_start_with_optional_business_logging(config_dir, bizlog_enabled):
    root = config_dir(
        {
            "modules": {"enabled": ["framework", "system"]},
            "expression": {"enabled": True},
            "config": {
                "models": {
                    "database": {
                        "enabled": True,
                        "id_strategy": "snowflake",
                        "snowflake_machine_id": 913,
                        "sources": [
                            {
                                "name": "primary",
                                "url": "sqlite+aiosqlite:///:memory:",
                                "role": "primary",
                                "weight": 100,
                                "pool": None,
                                "tls": None,
                            }
                        ],
                    },
                    "security": {"enabled": True, "bizlog_enabled": bizlog_enabled},
                    "data_permission": {"enabled": True},
                }
            },
        }
    )
    app = StarterServer.create_app(base_dir=root, environ={}, steps=APP_BOOTSTRAP_STEPS[:3])
    async with app.router.lifespan_context(app):
        application = app.state.application_context
        with application.execution():
            role = ApplicationContext.lookup(RoleService)
            user = ApplicationContext.lookup(AdminUserService)
            assert isinstance(role, RoleService)
            assert isinstance(user, AdminUserService)
            if bizlog_enabled:
                audit = ApplicationContext.lookup(BizLogService)
                assert audit is application.get_bean(BizLogService)
            else:
                assert application.container.get_optional(BizLogService) is None
