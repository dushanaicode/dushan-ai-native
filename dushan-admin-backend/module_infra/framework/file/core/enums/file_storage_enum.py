from __future__ import annotations

from framework.common.enums.base_enum import BaseEnum
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.framework.file.core.client.db.db_file_client import DBFileClient
from module_infra.framework.file.core.client.db.db_file_client_config import DBFileClientConfig
from module_infra.framework.file.core.client.file_client_config import FileClientConfig
from module_infra.framework.file.core.client.ftp.ftp_file_client import FtpFileClient
from module_infra.framework.file.core.client.ftp.ftp_file_client_config import FtpFileClientConfig
from module_infra.framework.file.core.client.local.local_file_client import LocalFileClient
from module_infra.framework.file.core.client.local.local_file_client_config import (
    LocalFileClientConfig,
)
from module_infra.framework.file.core.client.s3.s3_file_client import S3FileClient
from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig
from module_infra.framework.file.core.client.sftp.sftp_file_client import SftpFileClient
from module_infra.framework.file.core.client.sftp.sftp_file_client_config import (
    SftpFileClientConfig,
)


class FileStorageEnum(BaseEnum):
    DB = (1, "DB", DBFileClientConfig, DBFileClient)
    LOCAL = (10, "LOCAL", LocalFileClientConfig, LocalFileClient)
    FTP = (11, "FTP", FtpFileClientConfig, FtpFileClient)
    SFTP = (12, "SFTP", SftpFileClientConfig, SftpFileClient)
    S3 = (20, "S3", S3FileClientConfig, S3FileClient)

    def __new__(
        cls,
        storage: int,
        label: str,
        config_class: type[FileClientConfig],
        client_class: type[AbstractFileClient],
    ):
        self = object.__new__(cls)
        self._value_ = storage
        self._label_ = label
        self._config_class = config_class
        self._client_class = client_class
        return self

    @property
    def storage(self):
        return self.code

    @property
    def config_class(self) -> type[FileClientConfig]:
        return self._config_class

    @property
    def client_class(self) -> type[AbstractFileClient]:
        return self._client_class

    @classmethod
    def get_by_storage(cls, storage: int) -> "FileStorageEnum | None":
        for item in cls:
            if item.code == storage:
                return item
        return None
