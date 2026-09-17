from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class FilePresignedUrlReqVO(BaseRequestVO):
    """管理后台 - 获取文件预签名地址 Request VO"""

    name: Annotated[str, Field(..., description="文件名称")]
    directory: Annotated[str | None, Field(None, description="文件目录")]
