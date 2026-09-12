import ssl
from pathlib import Path

from pydantic import model_validator

from framework.starter_config.config.config_model import ConfigModel


class DatabaseTlsSettings(ConfigModel):
    """启用 TLS 时始终验证服务端证书与主机名，可选双向证书。"""

    ca_file: Path | None
    certificate_file: Path | None
    private_key_file: Path | None

    @model_validator(mode="after")
    def validate_files(self):
        if (self.certificate_file is None) != (self.private_key_file is None):
            raise ValueError("客户端证书和私钥必须成对配置")
        if any(
            path is not None and not path.is_absolute()
            for path in (self.ca_file, self.certificate_file, self.private_key_file)
        ):
            raise ValueError("TLS 文件必须使用绝对路径")
        return self

    def create_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(cafile=self.ca_file)
        if self.certificate_file is not None:
            context.load_cert_chain(self.certificate_file, self.private_key_file)
        return context
