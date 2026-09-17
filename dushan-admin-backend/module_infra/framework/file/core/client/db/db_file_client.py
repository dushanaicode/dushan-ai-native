from sqlalchemy import func, select

from framework.common.utils.str.str_utils import StrUtils
from module_infra.dal.dataobject.file.file_content_do import FileContentDO
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient


class DBFileClient(AbstractFileClient):
    def __init__(self, identifier, config, mapper):
        super().__init__(identifier, config)
        self.mapper = mapper

    async def do_init(self):
        return None

    async def upload(self, path, content, file_type):
        path = self.key(path)
        await self.mapper.insert(FileContentDO(config_id=self._id, path=path, content=content))
        return self.format_file_url(self.config.domain, path)

    async def delete(self, path):
        await self.mapper.soft_delete_by_condition(
            FileContentDO.config_id == self._id, FileContentDO.path == self.key(path)
        )

    async def get_content(self, path):
        rows = await self.mapper.select_list_by_config_id_and_path(self._id, self.key(path))
        if not rows:
            raise FileNotFoundError(path)
        return rows[0].content

    async def list_objects(self, prefix="", delimiter="/"):
        prefix = self.key(prefix) if prefix else ""
        rows = (
            await self.mapper.read(
                select(
                    FileContentDO.path,
                    func.length(FileContentDO.content),
                    FileContentDO.create_time,
                ).where(
                    FileContentDO.config_id == self._id,
                    FileContentDO.path.like(StrUtils.escape_like(prefix) + "%"),
                )
            )
        ).all()
        files, directories = [], set()
        for path, size, created in rows:
            relative = path[len(prefix) :]
            if not relative:
                continue
            if delimiter and delimiter in relative:
                directories.add(prefix + relative.split(delimiter)[0] + delimiter)
            else:
                files.append(
                    {
                        "key": path,
                        "name": relative,
                        "size": size,
                        "lastModified": created.isoformat(),
                    }
                )
        return {
            "files": files,
            "directories": [
                {"prefix": d, "name": d[len(prefix) :].rstrip(delimiter)}
                for d in sorted(directories)
            ],
            "isTruncated": False,
            "nextMarker": "",
        }

    async def rename(self, old_key, new_key):
        old_key, new_key = self.key(old_key), self.key(new_key)
        if old_key.endswith("/"):
            return await self.mapper.rename_path_prefix(self._id, old_key, new_key)
        return await self.mapper.rename_path(self._id, old_key, new_key)
