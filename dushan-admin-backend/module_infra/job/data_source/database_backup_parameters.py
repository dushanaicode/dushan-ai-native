from typing import Literal

from pydantic import BaseModel, ConfigDict


class DatabaseBackupParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    backup_type: Literal["full", "incremental"] = "full"
