from module_system.controller.admin.tenant.vo.tenant.tenant_save_req_vo import TenantSaveReqVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO


class TenantConvert:
    @staticmethod
    def convert(tenant: TenantSaveReqVO) -> UserSaveReqVO:
        """将 TenantSaveReqVO 转换为 UserSaveReqVO"""
        return UserSaveReqVO(
            username=tenant.username, password=tenant.password, nickname=tenant.contact_name
        )
