from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO


class UserExportReqVO(UserPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
