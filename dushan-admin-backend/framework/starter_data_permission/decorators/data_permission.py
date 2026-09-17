from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.model.model_scanner import ModelScanner


def data_permission(
    *,
    permission_type,
    user_id_column=None,
    dept_id_column=None,
    description="",
    tenant_column="tenant_id",
    resource=None,
):
    """声明本人、部门或二者的记录范围；归属列支持整数及字符串 ID。"""
    expected = {"user_scope": (True, False), "dept_scope": (False, True), "both": (True, True)}
    if permission_type not in expected or expected[permission_type] != (
        user_id_column is not None,
        dept_id_column is not None,
    ):
        raise ValueError("数据权限类型与用户/部门归属列不一致")

    def mark(model):
        if "__data_permission__" in vars(model):
            raise ValueError("模型不能重复声明数据权限")
        model.__data_permission__ = DataPermissionModel(
            model, False, tenant_column, user_id_column, dept_id_column, resource
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
