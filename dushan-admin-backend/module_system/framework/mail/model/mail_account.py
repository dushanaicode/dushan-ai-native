import re
from dataclasses import dataclass, field


@dataclass
class MailAccount:
    """承载 SMTP 邮件账号、认证和 TLS 连接参数。"""

    host: str | None = None
    port: int | None = None
    auth: bool | None = None
    auth_mechanisms: str | None = None
    user: str | None = None
    password: str | None = None
    from_address: str | None = None
    debug: bool = False
    charset: str = "utf-8"
    encode_filename: bool = True
    starttls_enable: bool = False
    ssl_enable: bool | None = None
    ssl_protocols: str | None = None
    socket_factory_class: str = "javax.net.ssl.SSLSocketFactory"
    socket_factory_fallback: bool = False
    socket_factory_port: int = 465
    timeout: int = 0
    connection_timeout: int = 0
    write_timeout: int = 0
    custom_property: dict[str, str] = field(default_factory=dict)

    def set_custom_property(self, key: str, value: str):
        """设置自定义属性"""
        if key and value:
            self.custom_property[key] = value
        return self

    def get_smtp_props(self) -> dict[str, str]:
        """构造 SMTP 相关的配置字典，可供邮件发送库使用"""
        props = {"mail.transport.protocol": "smtp"}
        self._add_basic_smtp_props(props)
        self._add_ssl_smtp_props(props)
        props.update(self.custom_property)
        return props

    def default_if_empty(self):
        """根据发件人地址补齐 SMTP 默认配置。"""
        if not self.from_address or self.from_address.strip() == "":
            raise ValueError("'from_address' must not be blank!")
        if not self.host:
            self._fill_host_from_from_address()
        if not self.user:
            self.user = self.from_address
        if self.auth is None:
            self.auth = bool(self.password)
        if not self.port:
            self.port = (
                self.socket_factory_port if self.ssl_enable is not None and self.ssl_enable else 25
            )
        if not self.charset:
            self.charset = "utf-8"
        return self

    def _add_basic_smtp_props(self, props: dict[str, str]) -> None:
        """写入 SMTP 主机、端口、认证和超时配置。"""
        if self.host:
            props["mail.smtp.host"] = self.host
        if self.port:
            props["mail.smtp.port"] = str(self.port)
        if self.auth is not None:
            props["mail.smtp.auth"] = str(self.auth).lower()
        if self.auth_mechanisms:
            props["mail.smtp.auth.mechanisms"] = self.auth_mechanisms
        if self.timeout > 0:
            props["mail.smtp.timeout"] = str(self.timeout)
        if self.connection_timeout > 0:
            props["mail.smtp.connectiontimeout"] = str(self.connection_timeout)
        if self.write_timeout > 0:
            props["mail.smtp.writetimeout"] = str(self.write_timeout)
        props["mail.debug"] = str(self.debug).lower()

    def _add_ssl_smtp_props(self, props: dict[str, str]) -> None:
        """写入 SMTP SSL 和 STARTTLS 相关配置。"""
        if self.starttls_enable:
            props["mail.smtp.starttls.enable"] = "true"
            if self.ssl_enable is None:
                self.ssl_enable = True
        if not self.ssl_enable:
            return
        props["mail.smtp.ssl.enable"] = "true"
        props["mail.smtp.socketFactory.class"] = self.socket_factory_class
        props["mail.smtp.socketFactory.fallback"] = str(self.socket_factory_fallback).lower()
        props["smtp.socketFactory.port"] = str(self.socket_factory_port)
        if self.ssl_protocols:
            props["mail.smtp.ssl.protocols"] = self.ssl_protocols

    def _fill_host_from_from_address(self) -> None:
        """根据发件人邮箱域名推导 SMTP 主机。"""
        if self.from_address is None:
            raise ValueError("'from_address' must not be blank!")
        match = re.search("@(.+)", self.from_address)
        if match:
            self.host = f"smtp.{match.group(1)}"

    def __str__(self):
        """实现 __str__ 协议方法。"""
        pwd_str = "******" if self.password else ""
        return f"MailAccount [host={self.host}, port={self.port}, auth={self.auth}, user={self.user}, password={pwd_str}, from_address={self.from_address}, starttls_enable={self.starttls_enable}, socket_factory_class={self.socket_factory_class}, socket_factory_fallback={self.socket_factory_fallback}, socket_factory_port={self.socket_factory_port}]"
