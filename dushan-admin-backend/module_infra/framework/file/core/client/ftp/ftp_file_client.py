from contextlib import asynccontextmanager
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
            async for path, info in client.list(self._path(prefix) if prefix else self.base):
                relative = path.relative_to(self.base).as_posix()
                if info["type"] == "dir":
                    directories.append({"prefix": relative + "/", "name": path.name})
                elif info["type"] == "file":
                    files.append(
                        {
                            "key": relative,
                            "name": path.name,
                            "size": int(info["size"]),
                            "lastModified": info.get("modify"),
                        }
                    )
        return {"files": files, "directories": directories, "isTruncated": False, "nextMarker": ""}

    async def rename(self, old_key, new_key):
        async with self._client() as client:
            target = self._path(new_key)
            if await client.exists(target):
                raise FileExistsError(new_key)
            await client.make_directory(target.parent, parents=True)
            await client.rename(self._path(old_key), target)
