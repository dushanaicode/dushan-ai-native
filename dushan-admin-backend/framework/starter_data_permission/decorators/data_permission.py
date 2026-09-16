from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.model.model_scanner import ModelScanner


def data_permission(
    *, tenant_column="tenant_id", membership_column=None, department_column=None, resource=None
):
    """显式声明受保护模型；列名使用 Table column key，支持 ORM 属性重命名。"""

    def mark(model):
        if "__data_permission__" in vars(model):
            raise ValueError("模型不能重复声明数据权限")
        model.__data_permission__ = DataPermissionModel(
            model, False, tenant_column, membership_column, department_column, resource
        )
        return ModelScanner.mark(model)

    return mark


def public_data(*, tenant_column):
    """tenant_column=None 明确全局公开；给定列则仅在有效租户内公开。"""

    def mark(model):
        if "__data_permission__" in vars(model):
            raise ValueError("模型不能重复声明数据权限")
        model.__data_permission__ = DataPermissionModel(model, True, tenant_column)
        return ModelScanner.mark(model)

    return mark
