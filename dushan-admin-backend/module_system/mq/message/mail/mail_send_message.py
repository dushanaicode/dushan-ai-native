from typing import ClassVar

from pydantic import Field, field_validator

from framework.common.schemas.base_bo import BaseBO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull


class MailSendMessage(BaseBO):
    """
    邮箱发送消息模型
    """

    message_id: str = Field(..., description="消息唯一ID")
    log_id: int = Field(..., description="邮件日志编号")
    to_mails: list[str] = Field(..., description="接收邮件地址列表")
    cc_mails: list[str] | None = Field(None, description="抄送邮件地址列表")
    bcc_mails: list[str] | None = Field(None, description="密送邮件地址列表")
    account_id: int = Field(..., description="邮件账号编号")
    nickname: str | None = Field(None, description="邮件发件人")
    title: str = Field(..., description="邮件标题")
    content: str = Field(..., description="邮件内容")
    stream_key: ClassVar[str] = "mail:send"

    @field_validator("log_id", mode="before")
    @classmethod
    def _validate_log_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="log_id", value=v, error_msg="邮件日志编号不能为空")
        return v

    @field_validator("to_mails", mode="before")
    @classmethod
    def _validate_to_mails(cls, v: list[str]) -> list[str]:
        NotEmpty.require_not_empty(
            field_name="to_mails", value=v, error_msg="接收邮件地址列表不能为空"
        )
        return v

    @field_validator("account_id", mode="before")
    @classmethod
    def _validate_account_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="account_id", value=v, error_msg="邮件账号编号不能为空")
        return v

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="title", value=v, error_msg="邮件标题不能为空")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def _validate_content(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="content", value=v, error_msg="邮件内容不能为空")
        return v
