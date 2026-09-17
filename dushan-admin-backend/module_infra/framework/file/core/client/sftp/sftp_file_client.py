import stat
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import PurePosixPath

import asyncssh

from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient


class SftpFileClient(AbstractFileClient):
    async def do_init(self):
        self.base = PurePosixPath(self.config.base_path)

    @asynccontextmanager
    async def _client(self):
        async with asyncssh.connect(
            self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            known_hosts=self.config.known_hosts,
            client_keys=[],
            agent_path=None,
            config=[],
            connect_timeout=10,
        ) as connection:
            async with connection.start_sftp_client() as client:
                yield client

    def _path(self, path):
        return str(self.base / self.key(path))

    async def upload(self, path, content, file_type=None):
        target = self._path(path)
        async with self._client() as client:
            await client.makedirs(
                target if path.endswith("/") else str(PurePosixPath(target).parent), exist_ok=True
            )
            if not path.endswith("/"):
                async with client.open(target, "wb") as stream:
                    await stream.write(content)
        return self.format_file_url(self.config.domain, self.key(path))

    async def get_content(self, path):
        async with self._client() as client:
            async with client.open(self._path(path), "rb") as stream:
                return await stream.read()

    async def delete(self, path):
        async with self._client() as client:
            if path.endswith("/"):
                await client.rmdir(self._path(path))
            else:
                await client.remove(self._path(path))

    async def list_objects(self, prefix="", delimiter="/"):
        files, directories = [], []
        async with self._client() as client:
            for item in await client.readdir(self._path(prefix) if prefix else str(self.base)):
                if item.filename in {".", ".."}:
                    continue
                key = (self.key(prefix).rstrip("/") + "/" if prefix else "") + item.filename
                if stat.S_ISDIR(item.attrs.permissions):
                    directories.append({"prefix": key + "/", "name": item.filename})
                elif stat.S_ISREG(item.attrs.permissions):
                    files.append(
                        {
                            "key": key,
                            "name": item.filename,
                            "size": item.attrs.size,
                            "lastModified": datetime.fromtimestamp(
                                item.attrs.mtime, timezone.utc
                            ).isoformat(),
                        }
                    )
        return {"files": files, "directories": directories, "isTruncated": False, "nextMarker": ""}

    async def rename(self, old_key, new_key):
        async with self._client() as client:
            target = self._path(new_key)
            if await client.exists(target):
                raise FileExistsError(new_key)
            await client.makedirs(str(PurePosixPath(target).parent), exist_ok=True)
            await client.rename(self._path(old_key), target)
