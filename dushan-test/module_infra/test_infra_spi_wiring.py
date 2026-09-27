import pytest

from framework.starter_auth.core.auth_service import AuthService
from framework.starter_captcha.core.captcha_service import CaptchaService
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_monitor.spi.monitor_provider import MonitorProvider
from framework.starter_security.spi.data_access_provider import DataAccessProvider
from framework.starter_security.spi.security_execution_provider import SecurityExecutionProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_tenant.spi.tenant_execution_provider import TenantExecutionProvider
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_all_enabled_consumers_share_registered_spi_instances(infra_app, admin_client):
    with infra_app.state.application_context.execution():
        container = infra_app.state.application_context.container
        monitor = container.get(MonitorProvider)
        security = container.get(SecurityExecutionProvider)
        tenant = container.get(TenantExecutionProvider)
        data_access = container.get(DataAccessProvider)
        tenant_access = container.get(TenantAccessProvider)
        assert security.service is infra_app.state.security
        assert tenant.service is tenant_access.service is infra_app.state.tenant
        assert data_access.service is container.get(DataPermissionService)
        assert infra_app.state.security._data_access is data_access
        assert infra_app.state.security._tenant is tenant_access
        assert container.get(AuthService).monitor is monitor
        assert container.get(CaptchaService).monitor is monitor
        assert infra_app.state.job.invoker.security is security
        assert infra_app.state.job.invoker.monitor is monitor
        assert infra_app.state.job.tenant_runner.tenant is tenant
        assert infra_app.state.mq.security is security
        assert infra_app.state.mq.monitor is monitor
        assert infra_app.state.mq.tenant is tenant
        assert infra_app.state.websocket.security is security
        assert infra_app.state.websocket.monitor is monitor
    assert (await admin_client.get("/health")).status_code == 200
    response = await admin_client.get("/admin-api/system/auth/get-permission-info")
    assert response.json()["code"] == 0, response.text


@pytest.mark.parametrize(
    "missing", [DataAccessProvider, MonitorProvider, SecurityExecutionProvider]
)
async def test_missing_required_spi_prevents_ready(infra_app, monkeypatch, missing):
    original = CandidateSelection.select

    # 只过滤 DI 元数据候选；扫描中的配置、错误码等并非 DI 类。
    def select(selection, components):
        retained = []
        for component in components:
            metadata = vars(component).get(DiComponentMetadata.ATTRIBUTE)
            if metadata is None or metadata.interface is not missing:
                retained.append(component)
        return original(selection, retained)

    monkeypatch.setattr(CandidateSelection, "select", select)
    app = create_app(base_dir=infra_app.state.bootstrap.base_dir, environ={})
    with pytest.raises(BootstrapError):
        async with app.router.lifespan_context(app):
            pytest.fail("必要 SPI 缺失不应继续启动")
    assert not app.state.bootstrap.ready
    assert app.state.application_context is None
