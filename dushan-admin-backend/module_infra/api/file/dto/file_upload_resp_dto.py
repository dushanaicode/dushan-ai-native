from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class FileUploadRespDTO(BaseDTO):
    """文件上传结果 DTO（跨模块使用）"""

    file_id: Annotated[int, Field(..., description="文件记录编号")]
    url: Annotated[str, Field(..., description="文件访问 URL")]
    config_id: Annotated[int, Field(..., description="文件存储配置编号")]
    storage_path: Annotated[str, Field(..., description="文件存储路径")]
