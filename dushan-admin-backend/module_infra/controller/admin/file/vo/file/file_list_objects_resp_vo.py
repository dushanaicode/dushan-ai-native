from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO
from module_infra.controller.admin.file.vo.file.file_object_vo import FileObjectVO


class FileListObjectsRespVO(BaseVO):
    """管理后台 - 文件管理 列举对象响应 VO"""

    objects: Annotated[
        list[FileObjectVO], Field(default_factory=list, description="合并的文件+目录列表")
    ]
    is_truncated: Annotated[bool, Field(default=False, description="是否截断")]
    next_marker: Annotated[str, Field(default="", description="下一页标记")]
    current_prefix: Annotated[str, Field(default="", description="当前前缀")]
