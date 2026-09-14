from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

type Authority = Annotated[str, Field(min_length=1, max_length=256)]


class PermissionSnapshot(BaseModel):
    """某一完整主体绑定及权威版本的权限；版本变化后旧缓存不可再被读取。"""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    binding: str
    revision: str
    permissions: frozenset[Authority] = Field(max_length=4096)
    roles: frozenset[Authority] = Field(max_length=1024)

    def __repr_args__(self):
        return iter(())
