from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class NoticePublisherInfoDTO(BaseDTO):
    """通知发布者信息快照。"""

    payload: Annotated[
        dict[str, Any], Field(default_factory=dict, description="发布者信息 JSON 快照")
    ]

    @classmethod
    def from_raw(cls, raw_info: dict[str, Any] | None) -> "NoticePublisherInfoDTO | None":
        """从原始存储字典恢复通知发布者信息。"""
        if raw_info is None:
            return None
        return cls(payload=raw_info)

    def to_storage_dict(self) -> dict[str, Any]:
        """将通知发布者信息转换为可存储字典。"""
        return self.payload
