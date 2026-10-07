from typing import Literal

from framework.common.schemas import BaseBO


class DatabaseBackupParameters(BaseBO):
    backup_type: Literal["full"] = "full"
