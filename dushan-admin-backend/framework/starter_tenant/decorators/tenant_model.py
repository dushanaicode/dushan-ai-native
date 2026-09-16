from framework.starter_database.model.model_scanner import ModelScanner
from framework.starter_tenant.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.model.tenant_model import TenantModel


def tenant_model(*, tenant_column="tenant_id"):
    """为单个模型显式声明租户归属，不从字段是否存在猜测。"""

    def mark(model):
        if "__tenant_model__" in vars(model):
            raise ValueError("模型租户归属重复声明")
        model.__tenant_model__ = TenantModel(model, TenantModelKind.TENANT, tenant_column)
        return ModelScanner.mark(model)

    return mark


def global_model(model):
    """声明全局控制数据；全局归属不赋予跨租户数据权限。"""
    if "__tenant_model__" in vars(model):
        raise ValueError("模型租户归属重复声明")
    model.__tenant_model__ = TenantModel(model, TenantModelKind.GLOBAL, None)
    return ModelScanner.mark(model)
