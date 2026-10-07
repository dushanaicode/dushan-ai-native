from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class ConfigDataKeyReqVO(BaseRequestVO):
    """管理后台 - 根据参数键名查询参数值 Request VO"""

    key: Annotated[str, Field(..., description="参数键名")]
