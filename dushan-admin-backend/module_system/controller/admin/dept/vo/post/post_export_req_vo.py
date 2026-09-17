from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class PostExportReqVO(PostPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
