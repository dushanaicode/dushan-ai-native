from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class FilePresignedUrlRespVO(BaseVO):
    """管理后台 - 文件预签名地址 Response VO"""

    config_id: Annotated[SnowflakeIdStr, Field(..., description="配置编号")]
    upload_url: Annotated[str, Field(..., description="文件上传 URL")]
    url: Annotated[str, Field(..., description="文件访问 URL")]
    path: Annotated[str, Field(..., description="文件路径")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "configId": 11,
                    "uploadUrl": "https://s3.cn-south-1.qiniucs.com/dushan/xxx.png?X-Amz-Algorithm=AWS4-HMAC",
                    "url": "https://test.dushan.cn/xxx.png",
                    "path": "xxx.png",
                }
            ]
        }
    }
