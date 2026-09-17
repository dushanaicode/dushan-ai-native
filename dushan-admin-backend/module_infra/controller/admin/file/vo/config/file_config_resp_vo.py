from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_serializer

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.utils.str.str_utils import StrUtils
from module_infra.framework.file.file_config_secrets import FileConfigSecrets


class FileConfigRespVO(BaseVO):
    """管理后台 - 文件配置信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    name: Annotated[str, Field(..., description="配置名")]
    storage: Annotated[int, Field(..., description="存储器，参见 FileStorageEnum 枚举类")]
    master: Annotated[bool, Field(..., description="是否为主配置")]
    config: Annotated[dict[str, Any], Field(..., description="存储配置")]
    remark: Annotated[str | None, Field(default=None, description="备注")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "S3 - 阿里云",
                    "storage": 1,
                    "master": True,
                    "config": {"key": "value"},
                    "remark": "备注",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_serializer("config")
    def public_config(self, value):
        return StrUtils.deep_transform_keys(FileConfigSecrets.public(value), StrUtils.to_camel_case)
