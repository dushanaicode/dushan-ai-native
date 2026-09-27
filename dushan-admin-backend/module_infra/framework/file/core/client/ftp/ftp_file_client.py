import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import PurePosixPath

import aioftp

from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient


class FtpFileClient(AbstractFileClient):
    async def do_init(self):
        self.base = PurePosixPath(self.config.base_path)

    @asynccontextmanager
    async def _client(self):
        async with aioftp.Client.context(
            self.config.host,
            self.config.port,
            user=self.config.username,
            password=self.config.password,
            connection_timeout=10,
            socket_timeout=30,
        ) as client:
            yield client

    def _path(self, path):
        return self.base / self.key(path)

    async def upload(self, path, content, file_type=None):
        target = self._path(path)
        async with self._client() as client:
            await client.make_directory(
                target if path.endswith("/") else target.parent, parents=True
            )
            if not path.endswith("/"):
                async with client.upload_stream(target) as stream:
                    await stream.write(content)
        return self.format_file_url(self.config.domain, self.key(path))

    async def get_content(self, path):
        async with self._client() as client:
            async with client.download_stream(self._path(path)) as stream:
                return await stream.read()

    async def delete(self, path):
        async with self._client() as client:
            if path.endswith("/"):
                await client.remove_directory(self._path(path))
            else:
                await client.remove_file(self._path(path))

    async def list_objects(self, prefix="", delimiter="/"):
        files, directories = [], []
        async with self._client() as client:
            directory = self._path(prefix) if prefix else self.base
            mlsd = True
            try:
                entries = await client.list(directory, raw_command="MLSD")
            except aioftp.StatusCodeError as error:
                if not error.received_codes[-1].matches("50x"):
                    raise
                entries = await client.list(directory, raw_command="LIST")
                mlsd = False
            for path, info in entries:
                relative = path.relative_to(self.base).as_posix()
                if info["type"] == "dir":
                    directories.append({"prefix": relative + "/", "name": path.name})
                elif info["type"] == "file":
                    files.append(
                        {
                            "key": relative,
                            "name": path.name,
                            "size": int(info["size"]),
                            # LIST 没有可确认的时区，保留文件列表但不猜测绝对时间。
                            "lastModified": self._modify_time(info.get("modify")) if mlsd else None,
                        }
                    )
        return {"files": files, "directories": directories, "isTruncated": False, "nextMarker": ""}

    @staticmethod
    def _modify_time(value: str | None) -> str | None:
        """MLSD modify 使用 UTC；超出 datetime 微秒精度的小数截断。"""
        if value is None:
            return None
        match = re.fullmatch(r"([0-9]{14})(?:\.([0-9]+))?", value)
        if match is None:
            raise ValueError("FTP MLSD modify 时间格式无效")
        instant = datetime.strptime(match[1], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        if match[2] is not None:
            instant = instant.replace(microsecond=int(match[2][:6].ljust(6, "0")))
        return instant.isoformat()

    async def rename(self, old_key, new_key):
        async with self._client() as client:
            target = self._path(new_key)
            if await client.exists(target):
                raise FileExistsError(new_key)
            await client.make_directory(target.parent, parents=True)
            await client.rename(self._path(old_key), target)
