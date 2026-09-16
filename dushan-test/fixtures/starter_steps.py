from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS
from server.bootstrap.steps.tenant_step import TenantStep


class StarterSteps:
    """组件独立测试显式选择资源步骤；租户集成测试使用完整默认装配。"""

    @staticmethod
    def without_tenant():
        return tuple(step for step in APP_BOOTSTRAP_STEPS if step.handler is not TenantStep.run)
