import pytest

from server.bootstrap.bootstrap_step_spec import APP_BOOTSTRAP_STEPS
from server.starter_server import StarterServer

pytestmark = pytest.mark.unit


async def test_enabled_business_modules_pass_i18n_integrity(config_dir):
    root = config_dir(
        {
            "modules": {"enabled": ["framework", "system", "infra"]},
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
                    "security": {"enabled": True},
                    "data_permission": {"enabled": True},
                }
            },
        }
    )
    app = StarterServer.create_app(base_dir=root, environ={}, steps=APP_BOOTSTRAP_STEPS[:3])
    async with app.router.lifespan_context(app):
        assert app.state.bootstrap.definitions.translator is not None
