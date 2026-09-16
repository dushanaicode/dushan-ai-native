import pytest

from framework.starter_tenant.exception.tenant_exception import TenantException
from server.starter_server import create_app


async def test_empty_framework_starts_without_database_or_fake_tenant(config_dir):
    app = create_app(base_dir=config_dir({"banner": {"enabled": False}}), environ={})
    async with app.router.lifespan_context(app):
        tenant = app.state.tenant
        assert tenant.settings.enabled is True
        assert not tenant.ready
        with app.state.application_context.execution():
            with pytest.raises(TenantException, match="上下文"):
                tenant.context.get_required_tenant_id()
            with pytest.raises(TenantException, match="未就绪"):
                await tenant.targets()
    assert app.state.tenant is None
