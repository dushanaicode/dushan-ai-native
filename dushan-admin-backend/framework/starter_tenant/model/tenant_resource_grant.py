from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TenantResourceGrant(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)
    resource: str = Field(min_length=1, max_length=256)
    actions: frozenset[Literal["select", "insert", "update", "delete"]] = Field(min_length=1)
