from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class CodegenPreviewRespVO(BaseVO):
    """管理后台 - 代码生成预览响应 VO"""

    file_path: Annotated[str, Field(..., description="文件路径")]
    code: Annotated[str, Field(..., description="代码内容")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "filePath": "module_system/dal/dataobject/user/user_do.py",
                    "code": "class UserDO(BaseDO): ...",
                }
            ]
        }
    }
