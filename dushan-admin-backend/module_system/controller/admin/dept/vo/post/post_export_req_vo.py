from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO


class PostExportReqVO(PostPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
