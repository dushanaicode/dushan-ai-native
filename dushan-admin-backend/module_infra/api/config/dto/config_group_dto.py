from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.schemas.base_dto import BaseDTO
from module_infra.api.config.dto.config_item_dto import ConfigItemDTO


class ConfigGroupDTO(BaseDTO):
    """配置分组 DTO"""

    type_id: Annotated[SnowflakeIdStr, Field(..., description="配置类型编号")]
    type_name: Annotated[str, Field(..., description="配置类型名称")]
    type_code: Annotated[str, Field(..., description="配置类型编码")]
    items: Annotated[list[ConfigItemDTO], Field(default_factory=list, description="配置项列表")]
