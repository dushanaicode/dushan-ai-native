from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class FilePresignedUrlRespDTO(BaseDTO):
    """文件预签名地址 Response DTO（跨模块使用）"""

    config_id: Annotated[int, Field(..., description="配置编号")]
    upload_url: Annotated[str, Field(..., description="文件上传 URL")]
    url: Annotated[str, Field(..., description="文件访问 URL")]
    path: Annotated[str, Field(..., description="文件路径")]
