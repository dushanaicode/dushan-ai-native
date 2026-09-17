from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from urllib.parse import quote


class AbstractFileClient(ABC):
    def __init__(self, identifier, config):
        self._id, self.config = identifier, config

    async def init(self):
        await self.do_init()

    @abstractmethod
    async def do_init(self): ...

    def get_id(self):
        return self._id

    @staticmethod
    def key(path):
        if (
            not path
            or path.startswith(("/", "\\"))
            or "\\" in path
            or ":" in path
            or "\x00" in path
            or any(p in {".", ".."} for p in path.split("/"))
        ):
            raise ValueError("文件路径必须是存储根目录内的相对路径")
        return PurePosixPath(path).as_posix() + ("/" if path.endswith("/") else "")

    def _sanitize_path(self, path):
        return PurePosixPath(self.key(path))

    def format_file_url(self, domain, path):
        return (
            f"{str(domain).rstrip('/')}/admin-api/infra/file/{self._id}/get/{quote(path, safe='/')}"
        )

    async def get_presigned_object_url(self, path):
        raise ValueError("当前存储不支持直传预签名")

    async def presign_get_url(self, path, expiration_seconds=None):
        return self.format_file_url(self.config.domain, self.key(path))

    async def close(self):
        return None
