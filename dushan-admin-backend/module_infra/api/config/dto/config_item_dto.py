from typing import Annotated

from pydantic import Field

from framework.common.contracts import SnowflakeIdStr
from framework.common.schemas import BaseDTO


class ConfigItemDTO(BaseDTO):
    """配置项 DTO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="配置编号")]
    name: Annotated[str, Field(..., description="配置名称")]
    config_key: Annotated[str, Field(..., description="配置键")]
    description: Annotated[str | None, Field(default=None, description="配置描述")]
    input_type: Annotated[str, Field(default="input", description="输入类型")]
    input_props: Annotated[str | None, Field(default=None, description="输入组件属性（JSON）")]
    content: Annotated[str | None, Field(default=None, description="配置值")]
    sort: Annotated[SnowflakeIdStr, Field(default=0, description="排序")]
