from __future__ import annotations

from sqlalchemy import select, update

from framework.common.enums.status_enum import StatusEnum
from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.file.vo.config.file_config_page_req_vo import FileConfigPageReqVO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO


@mapper()
class FileConfigMapper(BaseMapper[FileConfigDO]):
    def __init__(self):
        super().__init__(FileConfigDO)

    async def select_page(self, req_vo: FileConfigPageReqVO) -> PageResult[FileConfigDO]:
        """分页查询文件配置记录"""
        stmt = select(FileConfigDO)
        if req_vo.name:
            escaped = StrUtils.escape_like(req_vo.name)
            stmt = stmt.where(FileConfigDO.name.ilike(f"%{escaped}%"))
        if req_vo.storage is not None:
            stmt = stmt.where(FileConfigDO.storage == req_vo.storage)
        if req_vo.status is not None:
            stmt = stmt.where(FileConfigDO.status == req_vo.status)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                FileConfigDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(FileConfigDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_by_master(self) -> FileConfigDO | None:
        """查询主配置记录（master 为 True），仅查询未逻辑删除的数据"""
        stmt = select(FileConfigDO).where(FileConfigDO.master.is_(True))
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def update_batch(self, file_config: FileConfigDO) -> None:
        """批量更新文件配置记录"""
        stmt = (
            update(FileConfigDO)
            .where(FileConfigDO.deleted.is_(False))
            .values(master=file_config.master)
        )
        await self.write(stmt)

    async def select_list(self) -> list[FileConfigDO]:
        """根据条件获取文件配置列表"""
        stmt = select(FileConfigDO).where(FileConfigDO.status == StatusEnum.ENABLE.code)
        stmt = stmt.order_by(FileConfigDO.id.desc())
        result = await self.read(stmt)
        return list(result.scalars().all())
