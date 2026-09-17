from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class SysFilesVO(BaseVO):
    """管理后台 - 磁盘信息 VO"""

    dir_name: Annotated[str | None, Field(description="盘符路径")] = None
    sys_type_name: Annotated[str | None, Field(description="盘符类型")] = None
    type_name: Annotated[str | None, Field(description="文件类型")] = None
    total: Annotated[str | None, Field(description="总大小")] = None
    used: Annotated[str | None, Field(description="已经使用量")] = None
    free: Annotated[str | None, Field(description="剩余大小")] = None
    usage: Annotated[str | None, Field(description="资源的使用率")] = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dirName": "/",
                    "sysTypeName": "ext4",
                    "typeName": "本地磁盘",
                    "total": "500GB",
                    "used": "200GB",
                    "free": "300GB",
                    "usage": "40%",
                }
            ]
        }
    }
