from __future__ import annotations

from sqlalchemy import func, select

from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.common.utils.str.str_utils import StrUtils
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_di.decorators.components import mapper
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.dal.dataobject.file.file_do import FileDO


@mapper()
class FileMapper(BaseMapper[FileDO]):
    def __init__(self):
        super().__init__(FileDO)

    async def select_page(self, req_vo: FilePageReqVO) -> PageResult[FileDO]:
        """分页查询文件记录"""
        stmt = select(FileDO)
        if req_vo.path:
            escaped_path = StrUtils.escape_like(req_vo.path)
            stmt = stmt.where(FileDO.path.ilike(f"%{escaped_path}%"))
        if req_vo.file_type:
            escaped_type = StrUtils.escape_like(req_vo.file_type)
            stmt = stmt.where(FileDO.type.ilike(f"%{escaped_type}%"))
        if req_vo.config_id:
            stmt = stmt.where(FileDO.config_id == req_vo.config_id)
        if req_vo.create_time and len(req_vo.create_time) >= 2:
            stmt = stmt.where(
                FileDO.create_time.between(req_vo.create_time[0], req_vo.create_time[1])
            )
        stmt = stmt.order_by(FileDO.id.desc())
        return await self.paginate_query(stmt, req_vo)

    async def select_count_by_config_id(self, config_id: int) -> int:
        """根据配置ID统计文件数量"""
        stmt = select(func.count()).select_from(FileDO).where(FileDO.config_id == config_id)
        result = await self.read(stmt)
        return result.scalar_one_or_none() or 0

    async def select_by_storage_path(self, storage_path: str) -> FileDO | None:
        """根据 storage_path 精确查询文件"""
        stmt = select(FileDO).where(FileDO.storage_path == storage_path)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_url(self, url: str) -> FileDO | None:
        """根据 url 精确查询文件"""
        stmt = select(FileDO).where(FileDO.url == url)
        result = await self.read(stmt)
        return result.scalar_one_or_none()

    async def select_by_config_and_prefix(
        self, config_id: int, storage_path_prefix: str
    ) -> list[FileDO]:
        """按 config_id + storage_path 前缀查询（用于目录浏览时补充 DB 信息）"""
        stmt = select(FileDO).where(
            FileDO.config_id == config_id, FileDO.storage_path.like(f"{storage_path_prefix}%")
        )
        result = await self.read(stmt)
        return list(result.scalars().all())

    async def search_files(
        self,
        config_id: int,
        keyword: str,
        search_mode: str,
        prefix: str,
        page_no: int,
        page_size: int,
    ) -> PageResult[FileDO]:
        """搜索文件（模糊/前缀）"""
        stmt = select(FileDO).where(FileDO.config_id == config_id)
        if prefix:
            stmt = stmt.where(FileDO.storage_path.like(f"{prefix}%"))
        if keyword:
            if search_mode == "prefix":
                stmt = stmt.where(FileDO.name.like(f"{keyword}%"))
            else:
                escaped_kw = StrUtils.escape_like(keyword)
                stmt = stmt.where(FileDO.name.ilike(f"%{escaped_kw}%"))
        stmt = stmt.order_by(FileDO.create_time.desc())
        return await self.paginate_query(stmt, PageQuery(page=page_no, page_size=page_size))
