from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO
from module_infra.definitions.enums.config.config_module_enum import ConfigModuleEnum


class ConfigTypeModuleReqVO(BaseRequestVO):
    """管理后台 - 配置类型模块过滤 Request VO"""

    module: Annotated[ConfigModuleEnum | None, Field(None, description="所属模块标识过滤")]
