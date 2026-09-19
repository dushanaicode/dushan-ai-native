from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class WeappFilePresignedUrlReqVO(BaseRequestVO):
    """管理后台 - 获取文件预签名地址 Request VO"""

    name: Annotated[str, Field(..., description="文件名称")]
    directory: Annotated[str | None, Field(None, description="文件目录")]
    model_config = {
        "json_schema_extra": {"examples": [{"file": "文件对象", "directory": "XXX/YYY"}]}
    }
