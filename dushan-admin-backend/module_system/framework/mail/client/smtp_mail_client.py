import re
import uuid
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import parseaddr

import aiosmtplib
from loguru import logger

from module_system.framework.mail.model.mail_account import MailAccount
from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.framework.notification.delivery.delivery_uncertain_failure import (
    DeliveryUncertainFailure,
)


class SmtpMailClient:
    """封装邮件消息构建、SMTP 发送与异常归类。"""

    @staticmethod
    async def send(
        mail_account: MailAccount,
        to_emails: list[str],
        subject: str,
        content: str,
        is_html: bool = False,
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> str:
        """发送单封邮件并返回邮件服务器消息编号。"""
        message = SmtpMailClient._build_message(
            mail_account, to_emails, None, None, subject, content, is_html
        )
        return await SmtpMailClient._send_message(
            mail_account, message, to_emails, on_request_started, "SmtpMailClient.send"
        )

    @staticmethod
    async def send_multiple(
        mail_account: MailAccount,
        to_emails: list[str],
        cc_emails: list[str] | None,
        bcc_emails: list[str] | None,
        subject: str,
        content: str,
        is_html: bool = False,
        *,
        on_request_started: DeliveryRequestStartedCallback,
    ) -> str:
        """发送带抄送和密送收件人的邮件。"""
        message = SmtpMailClient._build_message(
            mail_account, to_emails, cc_emails, bcc_emails, subject, content, is_html
        )
        cc_list = cc_emails if cc_emails is not None else []
        bcc_list = bcc_emails if bcc_emails is not None else []
        recipients = to_emails + cc_list + bcc_list
        return await SmtpMailClient._send_message(
            mail_account, message, recipients, on_request_started, "SmtpMailClient.send_multiple"
        )

    @staticmethod
    def _build_message(
        mail_account: MailAccount,
        to_emails: list[str],
        cc_emails: list[str] | None,
        bcc_emails: list[str] | None,
        subject: str,
        content: str,
        is_html: bool,
    ) -> EmailMessage:
        """根据邮件账号和收件人信息构建标准邮件消息。"""
        message = EmailMessage()
        message["From"] = mail_account.from_address
        message["To"] = ", ".join(to_emails)
        if cc_emails:
            message["Cc"] = ", ".join(cc_emails)
        message["Subject"] = subject
        message.set_charset(mail_account.charset if mail_account.charset else "utf-8")
        if is_html:
            message.add_alternative(content, subtype="html")
        else:
            message.set_content(content)
        return message

    @staticmethod
    async def _send_message(
        mail_account: MailAccount,
        message: EmailMessage,
        recipients: list[str],
        on_request_started: DeliveryRequestStartedCallback,
        operation_name: str,
    ) -> str:
        """在 SMTP DATA 前完成连接、认证和地址拒绝判定。"""
        smtp = aiosmtplib.SMTP(
            hostname=mail_account.host,
            port=mail_account.port,
            username=mail_account.user,
            password=mail_account.password,
            use_tls=SmtpMailClient._use_implicit_tls(mail_account),
            start_tls=SmtpMailClient._use_explicit_starttls(mail_account),
            timeout=SmtpMailClient._resolve_timeout(mail_account),
        )
        request_started = False
        try:
            await smtp.connect()
            sender = parseaddr(mail_account.from_address)[1]
            await smtp.mail(sender)
            for recipient in recipients:
                await smtp.rcpt(recipient)
            await on_request_started()
            request_started = True
            response = await smtp.data(message.as_bytes(policy=SMTP_POLICY))
            return SmtpMailClient._extract_message_id(response.message)
        except DeliveryCancelled:
            raise
        except aiosmtplib.SMTPDataError as error:
            SmtpMailClient._log_send_exception(operation_name, mail_account, error)
            raise DeliveryDefiniteFailure(str(error)) from error
        except Exception as error:
            SmtpMailClient._log_send_exception(operation_name, mail_account, error)
            failure_type = DeliveryUncertainFailure if request_started else DeliveryDefiniteFailure
            raise failure_type(str(error)) from error
        finally:
            smtp.close()

    @staticmethod
    def _use_implicit_tls(mail_account: MailAccount) -> bool:
        """判断当前账号是否使用隐式 TLS 连接。"""
        if mail_account.port == 465:
            return True
        return mail_account.ssl_enable is True and (not mail_account.starttls_enable)

    @staticmethod
    def _use_explicit_starttls(mail_account: MailAccount) -> bool:
        """判断当前账号是否使用显式 STARTTLS 升级连接。"""
        return bool(mail_account.starttls_enable and mail_account.port != 465)

    @staticmethod
    def _resolve_timeout(mail_account: MailAccount) -> float:
        """解析 SMTP 发送超时时间。"""
        if mail_account.timeout and mail_account.timeout > 0:
            return float(mail_account.timeout / 1000)
        return 60.0

    @staticmethod
    def _extract_message_id(message_sent_str: str) -> str:
        """从 SMTP 返回文本中提取消息编号。"""
        message_id_match = re.search(
            "(?:id=|as\\s|queued as\\s)([a-zA-Z0-9\\-._@<>]+)", message_sent_str, re.IGNORECASE
        )
        if message_id_match:
            return message_id_match.group(1)
        return f"no-id-found-{uuid.uuid4().hex}"

    @staticmethod
    def _log_send_exception(operation_name: str, mail_account: MailAccount, exc: Exception) -> None:
        """按 SMTP 异常类型输出可定位的发送失败日志。"""
        if isinstance(exc, aiosmtplib.SMTPConnectError):
            logger.error(
                "【{}】无法连接到SMTP服务器 {}:{}, 原因: {}",
                operation_name,
                mail_account.host,
                mail_account.port,
                exc,
            )
            return
        if isinstance(exc, aiosmtplib.SMTPHeloError):
            logger.error(
                "【{}】SMTP HELO/EHLO 命令失败于 {}:{}, 原因: {}",
                operation_name,
                mail_account.host,
                mail_account.port,
                exc,
            )
            return
        if isinstance(exc, aiosmtplib.SMTPAuthenticationError):
            logger.error(
                "【{}】SMTP认证失败，用户 {} 于 {}:{}, 原因: {}",
                operation_name,
                mail_account.user,
                mail_account.host,
                mail_account.port,
                exc,
            )
            return
        if isinstance(exc, aiosmtplib.SMTPSenderRefused):
            logger.error(
                "【{}】发件人地址 {} 被服务器 {} 拒绝",
                operation_name,
                exc.sender,
                mail_account.host,
            )
            return
        if isinstance(exc, aiosmtplib.SMTPRecipientsRefused):
            logger.error(
                "【{}】一个或多个收件人被服务器 {} 拒绝: {}",
                operation_name,
                mail_account.host,
                exc.recipients,
            )
            return
        if isinstance(exc, aiosmtplib.SMTPResponseException):
            logger.error(
                "【{}】SMTP响应异常 (code {}) 来自 {}: {}",
                operation_name,
                exc.code,
                mail_account.host,
                exc.message,
            )
            return
        if isinstance(exc, ConnectionResetError):
            logger.error(
                "【{}】与SMTP服务器 {}:{} 的连接被重置",
                operation_name,
                mail_account.host,
                mail_account.port,
            )
            return
        if isinstance(exc, OSError):
            SmtpMailClient._log_os_error(operation_name, mail_account, exc)
            return
        logger.error("【{}】邮件发送过程中发生未知错误: {}", operation_name, exc)

    @staticmethod
    def _log_os_error(operation_name: str, mail_account: MailAccount, exc: OSError) -> None:
        """记录网络层和 TLS 配置相关的系统异常。"""
        logger.error(
            "【{}】连接到SMTP服务器 {}:{} 时发生OS/Socket错误",
            operation_name,
            mail_account.host,
            mail_account.port,
        )
        if "Unexpected EOF" in str(exc) or "EOF" in str(exc).upper():
            logger.debug(
                "【{}】检测到EOF错误。请检查TLS/SSL配置：端口465使用use_tls，端口587/25按需使用start_tls。",
                operation_name,
            )
