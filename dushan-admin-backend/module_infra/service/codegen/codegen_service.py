from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.codegen.vo.codegen_create_list_req_vo import (
    CodegenCreateListReqVO,
)
from module_infra.controller.admin.codegen.vo.codegen_database_table_resp_vo import (
    DatabaseTableRespVO,
)
from module_infra.controller.admin.codegen.vo.codegen_preview_resp_vo import CodegenPreviewRespVO
from module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo import CodegenTablePageReqVO
from module_infra.controller.admin.codegen.vo.codegen_update_req_vo import CodegenUpdateReqVO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO


@runtime_checkable
class CodegenService(Protocol):
    """代码生成服务接口"""

    async def create_codegen_list(self, req_vo: CodegenCreateListReqVO) -> list[int]:
        """批量导入数据库表"""
        ...

    async def update_codegen_table(self, req_vo: CodegenUpdateReqVO) -> None:
        """更新代码生成配置"""
        ...

    async def delete_codegen_table(self, table_id: int) -> None:
        """删除代码生成表"""
        ...

    async def delete_codegen_table_list(self, table_ids: list[int]) -> None:
        """批量删除代码生成表"""
        ...

    async def get_codegen_table_page(
        self, req_vo: CodegenTablePageReqVO
    ) -> PageResult[CodegenTableDO]:
        """分页查询代码生成表"""
        ...

    async def get_codegen_table(self, table_id: int) -> CodegenTableDO | None:
        """获取代码生成表"""
        ...

    async def get_codegen_detail(self, table_id: int) -> dict:
        """获取代码生成详情（表+列）"""
        ...

    async def get_codegen_table_list(self, data_source_config_id: int) -> list[CodegenTableDO]:
        """获取某数据源下的代码生成表列表"""
        ...

    async def get_schema_table_list(
        self, data_source_config_id: int, table_name: str | None, table_comment: str | None
    ) -> list[DatabaseTableRespVO]:
        """获取数据库的表列表（未导入的）"""
        ...

    async def sync_codegen_from_db(self, table_id: int) -> None:
        """从数据库同步表结构"""
        ...

    async def preview_codegen(self, table_id: int) -> list[CodegenPreviewRespVO]:
        """预览代码"""
        ...

    async def download_codegen(self, table_id: int) -> bytes:
        """下载生成代码 (zip)"""
        ...
