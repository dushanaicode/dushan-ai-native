from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class ScopeKeyValue(BaseVO):
    """管理后台 - OAuth2 Scope 键值对 VO"""

    key: Annotated[str, Field(..., description="scope 标识")]
    value: Annotated[str, Field(..., description="scope 描述")]
