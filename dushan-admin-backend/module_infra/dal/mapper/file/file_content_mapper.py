from __future__ import annotations

from sqlalchemy import func, select, update

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_infra.dal.dataobject.file.file_content_do import FileContentDO


@mapper()
class FileContentMapper(BaseMapper[FileContentDO]):
    def __init__(self):
        super().__init__(FileContentDO)

    async def logical_delete_by_config_id_and_path(self, config_id: int, path: str) -> None:
        """逻辑删除指定配置 ID 和路径的文件内容记录"""
        stmt = (
            update(FileContentDO)
            .where(
                FileContentDO.config_id == config_id,
                FileContentDO.path == path,
                FileContentDO.deleted.is_(False),
            )
            .values(deleted=True)
        )
        await self.write(stmt)

    async def select_list_by_config_id_and_path(
        self, config_id: int, path: str
    ) -> list[FileContentDO]:
        """查询指定配置 ID 和路径的文件内容列表（强制主库读，保证写后读一致性）"""
        stmt = select(FileContentDO).where(
            FileContentDO.config_id == config_id, FileContentDO.path == path
        )
        result = await self.read_from_primary(stmt)
        return list(result.scalars().all())

    async def rename_path(self, config_id: int, old_path: str, new_path: str) -> int:
        """重命名单个文件路径"""
        stmt = (
            update(FileContentDO)
            .where(
                FileContentDO.config_id == config_id,
                FileContentDO.path == old_path,
                FileContentDO.deleted.is_(False),
            )
            .values(path=new_path)
        )
        result = await self.write(stmt)
        return result.rowcount

    async def rename_path_prefix(self, config_id: int, old_prefix: str, new_prefix: str) -> int:
        """批量重命名目录前缀：将所有 old_prefix 开头的路径替换为 new_prefix"""
        stmt = (
            update(FileContentDO)
            .where(
                FileContentDO.config_id == config_id,
                FileContentDO.path.like(f"{old_prefix}%"),
                FileContentDO.deleted.is_(False),
            )
            .values(
                path=func.concat(new_prefix, func.substr(FileContentDO.path, len(old_prefix) + 1))
            )
        )
        result = await self.write(stmt)
        return result.rowcount
