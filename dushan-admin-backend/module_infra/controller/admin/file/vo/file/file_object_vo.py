from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum


class FileObjectVO(BaseVO):
    """文件/目录对象信息"""

    key: Annotated[str, Field(..., description="完整路径 key")]
    name: Annotated[str, Field(..., description="文件名/目录名")]
    size: Annotated[int | None, Field(default=None, description="文件大小（字节），目录为 None")]
    last_modified: Annotated[str | None, Field(default=None, description="最后修改时间")]
    type: Annotated[str | None, Field(default=None, description="MIME 类型")]
    is_directory: Annotated[bool, Field(default=False, description="是否为目录")]
    url: Annotated[str | None, Field(default=None, description="访问地址（文件才有）")]
    visibility: Annotated[
        FileVisibilityEnum | None,
        Field(default=None, description="可见性（目录和未登记对象为 None）"),
    ]
