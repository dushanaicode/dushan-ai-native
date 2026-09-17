from framework.common.enums.base_enum import BaseEnum


class RoleCodeEnum(BaseEnum):
    SUPER_ADMIN = ("super_admin", "超级管理员")
    TENANT_ADMIN = ("tenant_admin", "租户管理员")
    CRM_ADMIN = ("crm_admin", "CRM 管理员")

    @classmethod
    def array(cls) -> list[str]:
        """返回所有枚举项的 status 列表"""
        return [item.code for item in cls]

    @classmethod
    def is_super_admin(cls, code: str | None) -> bool:
        """
        判断给定的角色编码是否为超级管理员。
        """
        return code is not None and code.lower() == cls.SUPER_ADMIN.code.lower()
