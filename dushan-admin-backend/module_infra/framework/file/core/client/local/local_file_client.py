import asyncio
from datetime import datetime, timezone
from pathlib import Path

from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient


class LocalFileClient(AbstractFileClient):
    async def do_init(self):
        self._base_path = Path(self.config.base_path).resolve()
        await asyncio.to_thread(self._base_path.mkdir, parents=True, exist_ok=True)

    def _get_absolute_path(self, key):
        path = (self._base_path / self.key(key)).resolve()
        if not path.is_relative_to(self._base_path) or path == self._base_path:
            raise ValueError("文件路径越过配置的存储根目录")
        return path

    async def upload(self, path, content, file_type=None):
        target = self._get_absolute_path(path)
        if path.endswith("/"):
            await asyncio.to_thread(target.mkdir, parents=True, exist_ok=True)
        else:
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(target.write_bytes, content)
        return self.format_file_url(self.config.domain, self.key(path))

    async def get_content(self, path):
        return await asyncio.to_thread(self._get_absolute_path(path).read_bytes)

    async def delete(self, path):
        target = self._get_absolute_path(path)
        await asyncio.to_thread(target.rmdir if target.is_dir() else target.unlink)

    async def list_objects(self, prefix="", delimiter="/"):
        target = self._get_absolute_path(prefix) if prefix else self._base_path
        return await asyncio.to_thread(self._list, target)

    def _list(self, target):
        files, directories = [], []
        for item in sorted(target.iterdir()):
            if not item.resolve().is_relative_to(self._base_path):
                continue
            relative = item.relative_to(self._base_path).as_posix()
            if item.is_dir():
                directories.append({"prefix": relative + "/", "name": item.name})
            elif item.is_file():
                info = item.stat()
                files.append(
                    {
                        "key": relative,
                        "name": item.name,
                        "size": info.st_size,
                        "lastModified": datetime.fromtimestamp(
                            info.st_mtime, timezone.utc
                        ).isoformat(),
                    }
                )
        return {"files": files, "directories": directories, "isTruncated": False, "nextMarker": ""}

    async def rename(self, old_key, new_key):
        old, new = self._get_absolute_path(old_key), self._get_absolute_path(new_key)
        if new.exists():
            raise FileExistsError(new_key)
        await asyncio.to_thread(new.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(old.rename, new)
