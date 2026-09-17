from collections.abc import Collection
from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class NotificationChannelResult(BaseDTO):
    """单个通知渠道的用户级分发结果。"""

    channel_code: Annotated[str, Field(..., description="通知渠道编码")]
    success_user_ids: Annotated[
        set[int], Field(default_factory=set, description="发送成功的用户 ID")
    ]
    failed_user_ids: Annotated[
        set[int], Field(default_factory=set, description="发送失败的用户 ID")
    ]
    skipped_user_ids: Annotated[
        set[int], Field(default_factory=set, description="跳过发送的用户 ID")
    ]
    failure_reasons: Annotated[
        list[str], Field(default_factory=list, description="失败或跳过原因摘要")
    ]

    @property
    def success_count(self) -> int:
        """统计通知渠道成功送达的用户数量。"""
        return len(self.success_user_ids)

    @property
    def fail_count(self) -> int:
        """统计通知渠道失败的用户数量。"""
        return len(self.failed_user_ids) + len(self.skipped_user_ids)

    @property
    def unsuccessful_user_ids(self) -> set[int]:
        """合并通知渠道跳过和失败的用户编号。"""
        return self.failed_user_ids | self.skipped_user_ids

    @classmethod
    def skipped(
        cls, channel_code: str, user_ids: Collection[int], reason: str
    ) -> "NotificationChannelResult":
        """构造通知渠道跳过结果。"""
        return cls(
            channel_code=channel_code, skipped_user_ids=set(user_ids), failure_reasons=[reason]
        )

    @classmethod
    def failed(
        cls, channel_code: str, user_ids: Collection[int], reason: str
    ) -> "NotificationChannelResult":
        """构造通知渠道失败结果。"""
        return cls(
            channel_code=channel_code, failed_user_ids=set(user_ids), failure_reasons=[reason]
        )
