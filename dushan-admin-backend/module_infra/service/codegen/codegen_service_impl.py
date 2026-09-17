from __future__ import annotations

from typing import override

from loguru import logger

from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_infra.controller.admin.codegen.vo.codegen_create_list_req_vo import (
    CodegenCreateListReqVO,
)
from module_infra.controller.admin.codegen.vo.codegen_database_table_resp_vo import (
    DatabaseTableRespVO,
)
from module_infra.controller.admin.codegen.vo.codegen_preview_resp_vo import CodegenPreviewRespVO
from module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo import CodegenTablePageReqVO
from module_infra.controller.admin.codegen.vo.codegen_update_req_vo import CodegenUpdateReqVO
from module_infra.dal.dataobject.codegen.codegen_column_do import CodegenColumnDO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.dal.mapper.codegen.codegen_column_mapper import CodegenColumnMapper
from module_infra.dal.mapper.codegen.codegen_table_mapper import CodegenTableMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.codegen.codegen_service import CodegenService
from module_infra.service.codegen.inner.inner_codegen_builder import CodegenBuilder
from module_infra.service.codegen.inner.inner_codegen_engine import CodegenEngine
from module_infra.service.codegen.inner.inner_db_schema_reader import DbSchemaReader
from module_infra.service.data_source.data_source_config_service import DataSourceConfigService


@service(interface=CodegenService)
class CodegenServiceImpl(CodegenService):
    """代码生成服务实现类"""

    codegen_table_mapper: CodegenTableMapper = Inject()
    codegen_column_mapper: CodegenColumnMapper = Inject()
    data_source_config_service: DataSourceConfigService = Inject()
    db_schema_reader: DbSchemaReader = Inject()
    codegen_builder: CodegenBuilder = Inject()
    codegen_engine: CodegenEngine = Inject()

    @override
    @transactional
    async def create_codegen_list(self, req_vo: CodegenCreateListReqVO) -> list[int]:
        """批量导入数据库表"""
        data_source_config = await self.data_source_config_service.get_data_source_config(
            req_vo.data_source_config_id
        )
        if not data_source_config:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_DATA_NOT_EXISTS)
        table_ids = []
        for table_name in req_vo.table_names:
            existing = await self.codegen_table_mapper.select_by_table_name_and_data_source(
                table_name, req_vo.data_source_config_id
            )
            if existing:
                logger.debug(f"【CodegenServiceImpl】表 {table_name} 已导入，跳过")
                continue
            db_columns = await self.db_schema_reader.get_table_columns(
                data_source_config, table_name
            )
            if not db_columns:
                logger.warning(f"【CodegenServiceImpl】表 {table_name} 无字段，跳过")
                continue
            table_comment = await self.db_schema_reader.get_table_comment(
                data_source_config, table_name
            )
            table_do = CodegenTableDO()
            table_do.data_source_config_id = req_vo.data_source_config_id
            table_do.table_name = table_name
            table_do.table_comment = table_comment
            table_do.class_name = CodegenBuilder.build_class_name(table_name)
            table_do.module_name = CodegenBuilder.build_module_name(table_name)
            table_do.business_name = CodegenBuilder.build_business_name(table_name)
            table_do.class_comment = CodegenBuilder.build_class_comment(table_comment)
            table_do.author = "admin"
            table_do.template_type = 1
            table_do.front_type = 0
            table_do.scene = 1
            await self.codegen_table_mapper.insert(table_do)
            for idx, db_col in enumerate(db_columns):
                column_do = CodegenColumnDO()
                column_do.table_id = table_do.id
                column_do.computed_expression = db_col["computed_expression"]
                column_do.computed_persisted = db_col["computed_persisted"]
                column_do.column_name = db_col["column_name"]
                column_do.column_comment = db_col["column_comment"]
                column_do.data_type = db_col["data_type"]
                column_do.field_type = CodegenBuilder.map_field_type(db_col["data_type"])
                column_do.field_name = CodegenBuilder.build_field_name(db_col["column_name"])
                column_do.primary_key = CodegenBuilder.is_primary_key(db_col["column_key"])
                column_do.create_operation = CodegenBuilder.should_create_operation(
                    db_col["column_name"]
                )
                column_do.update_operation = CodegenBuilder.should_update_operation(
                    db_col["column_name"]
                )
                column_do.list_operation_result = CodegenBuilder.should_list_operation_result(
                    db_col["column_name"]
                )
                column_do.list_operation = False
                column_do.list_operation_condition = "="
                column_do.nullable = db_col["is_nullable"]
                column_do.column_size = db_col.get("column_size")
                column_do.html_type = CodegenBuilder.build_html_type(
                    db_col["column_name"], db_col["data_type"]
                )
                column_do.order_no = idx
                await self.codegen_column_mapper.insert(column_do)
            table_ids.append(table_do.id)
            logger.info(f"【CodegenServiceImpl】成功导入表: {table_name}, ID={table_do.id}")
        return table_ids

    @override
    @transactional
    async def update_codegen_table(self, req_vo: CodegenUpdateReqVO) -> None:
        """更新代码生成配置"""
        table_do = await self._validate_table_exists(req_vo.table.id)
        update_table_data = req_vo.table.model_dump(
            exclude={"id", "create_time", "update_time"}, exclude_unset=True, by_alias=False
        )
        for field, value in update_table_data.items():
            setattr(table_do, field, value)
        await self.codegen_table_mapper.update_by_id(table_do)
        for column_vo in req_vo.columns:
            column_do = await self.codegen_column_mapper.select_by_id(column_vo.id)
            if column_do is None or column_do.table_id != table_do.id:
                raise ValueError("字段不属于当前代码生成表")
            update_column_data = column_vo.model_dump(
                exclude={
                    "id",
                    "table_id",
                    "column_name",
                    "data_type",
                    "order_no",
                    "primary_key",
                    "create_time",
                    "update_time",
                },
                exclude_unset=True,
                by_alias=False,
            )
            for field, value in update_column_data.items():
                setattr(column_do, field, value)
            await self.codegen_column_mapper.update_by_id(column_do)
        logger.info(f"【CodegenServiceImpl】更新代码生成配置: tableId={req_vo.table.id}")

    @override
    @transactional
    async def delete_codegen_table(self, table_id: int) -> None:
        """删除代码生成表"""
        await self._validate_table_exists(table_id)
        await self.codegen_table_mapper.delete_by_id(table_id)
        await self.codegen_column_mapper.delete_by_table_id(table_id)
        logger.info(f"【CodegenServiceImpl】删除代码生成配置: tableId={table_id}")

    @override
    @transactional
    @transactional
    async def delete_codegen_table_list(self, table_ids: list[int]) -> None:
        """批量删除代码生成表"""
        for table_id in table_ids:
            await self.delete_codegen_table(table_id)

    @override
    async def get_codegen_table_page(
        self, req_vo: CodegenTablePageReqVO
    ) -> PageResult[CodegenTableDO]:
        """分页查询代码生成表"""
        return await self.codegen_table_mapper.select_page(req_vo)

    @override
    async def get_codegen_table(self, table_id: int) -> CodegenTableDO | None:
        """获取代码生成表"""
        return await self.codegen_table_mapper.select_by_id(table_id)

    @override
    async def get_codegen_detail(self, table_id: int) -> dict:
        """获取代码生成详情（表+列）"""
        table = await self._validate_table_exists(table_id)
        columns = await self.codegen_column_mapper.select_list_by_table_id(table_id)
        return {"table": table, "columns": columns}

    @override
    async def get_codegen_table_list(self, data_source_config_id: int) -> list[CodegenTableDO]:
        """获取某数据源下的代码生成表列表"""
        return await self.codegen_table_mapper.select_list_by_data_source_config_id(
            data_source_config_id
        )

    @override
    async def get_schema_table_list(
        self,
        data_source_config_id: int,
        table_name: str | None = None,
        table_comment: str | None = None,
    ) -> list[DatabaseTableRespVO]:
        """获取数据库的表列表（未导入的）"""
        data_source_config = await self.data_source_config_service.get_data_source_config(
            data_source_config_id
        )
        if not data_source_config:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_DATA_NOT_EXISTS)
        db_tables = await self.db_schema_reader.get_table_list(
            data_source_config, table_name, table_comment
        )
        imported_tables = await self.codegen_table_mapper.select_list_by_data_source_config_id(
            data_source_config_id
        )
        imported_names = {t.table_name for t in imported_tables}
        result = []
        for t in db_tables:
            if t["name"] not in imported_names:
                result.append(DatabaseTableRespVO(name=t["name"], comment=t["comment"]))
        return result

    @override
    @transactional
    async def sync_codegen_from_db(self, table_id: int) -> None:
        """从数据库同步表结构"""
        table_do = await self._validate_table_exists(table_id)
        data_source_config = await self.data_source_config_service.get_data_source_config(
            table_do.data_source_config_id
        )
        if not data_source_config:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_DATA_NOT_EXISTS)
        db_columns = await self.db_schema_reader.get_table_columns(
            data_source_config, table_do.table_name
        )
        if not db_columns:
            raise ServiceException(ErrorCodeConstants.CODEGEN_SYNC_COLUMNS_NULL)
        existing_columns = await self.codegen_column_mapper.select_list_by_table_id(table_id)
        existing_map = {c.column_name: c for c in existing_columns}
        db_column_names = {c["column_name"] for c in db_columns}
        for idx, db_col in enumerate(db_columns):
            if db_col["column_name"] not in existing_map:
                column_do = CodegenColumnDO()
                column_do.table_id = table_id
                column_do.computed_expression = db_col["computed_expression"]
                column_do.computed_persisted = db_col["computed_persisted"]
                column_do.column_name = db_col["column_name"]
                column_do.column_comment = db_col["column_comment"]
                column_do.data_type = db_col["data_type"]
                column_do.field_type = CodegenBuilder.map_field_type(db_col["data_type"])
                column_do.field_name = CodegenBuilder.build_field_name(db_col["column_name"])
                column_do.primary_key = CodegenBuilder.is_primary_key(db_col["column_key"])
                column_do.create_operation = CodegenBuilder.should_create_operation(
                    db_col["column_name"]
                )
                column_do.update_operation = CodegenBuilder.should_update_operation(
                    db_col["column_name"]
                )
                column_do.list_operation_result = CodegenBuilder.should_list_operation_result(
                    db_col["column_name"]
                )
                column_do.list_operation = False
                column_do.list_operation_condition = "="
                column_do.nullable = db_col["is_nullable"]
                column_do.column_size = db_col.get("column_size")
                column_do.html_type = CodegenBuilder.build_html_type(
                    db_col["column_name"], db_col["data_type"]
                )
                column_do.order_no = idx
                await self.codegen_column_mapper.insert(column_do)
                logger.debug(f"【CodegenServiceImpl】同步新增列: {db_col['column_name']}")
            else:
                existing_col = existing_map[db_col["column_name"]]
                changed = False
                if (
                    existing_col.computed_expression != db_col["computed_expression"]
                    or existing_col.computed_persisted != db_col["computed_persisted"]
                ):
                    existing_col.computed_expression = db_col["computed_expression"]
                    existing_col.computed_persisted = db_col["computed_persisted"]
                    changed = True
                if existing_col.data_type != db_col["data_type"]:
                    existing_col.data_type = db_col["data_type"]
                    changed = True
                new_size = db_col.get("column_size")
                if existing_col.column_size != new_size:
                    existing_col.column_size = new_size
                    changed = True
                if changed:
                    await self.codegen_column_mapper.update_by_id(existing_col)
        for existing_col in existing_columns:
            if existing_col.column_name not in db_column_names:
                await self.codegen_column_mapper.delete_by_id(existing_col.id)
                logger.debug(f"【CodegenServiceImpl】同步删除列: {existing_col.column_name}")
        table_comment = await self.db_schema_reader.get_table_comment(
            data_source_config, table_do.table_name
        )
        if table_comment and table_do.table_comment != table_comment:
            table_do.table_comment = table_comment
            await self.codegen_table_mapper.update_by_id(table_do)
        logger.info(f"【CodegenServiceImpl】同步数据库结构完成: tableId={table_id}")

    @override
    async def preview_codegen(self, table_id: int) -> list[CodegenPreviewRespVO]:
        """预览代码"""
        table_do = await self._validate_table_exists(table_id)
        columns = await self.codegen_column_mapper.select_list_by_table_id(table_id)
        sub_tables = await self._load_sub_tables(table_do)
        files = self.codegen_engine.generate(table_do, columns, sub_tables=sub_tables)
        return [CodegenPreviewRespVO(file_path=f["filePath"], code=f["code"]) for f in files]

    @override
    async def download_codegen(self, table_id: int) -> bytes:
        """下载生成代码 (zip)"""
        table_do = await self._validate_table_exists(table_id)
        columns = await self.codegen_column_mapper.select_list_by_table_id(table_id)
        sub_tables = await self._load_sub_tables(table_do)
        return self.codegen_engine.generate_zip(table_do, columns, sub_tables=sub_tables)

    async def _validate_table_exists(self, table_id: int) -> CodegenTableDO:
        """校验代码生成表是否存在"""
        table = await self.codegen_table_mapper.select_by_id(table_id)
        if not table:
            raise ServiceException(ErrorCodeConstants.CODEGEN_TABLE_NOT_EXISTS)
        return table

    async def _load_sub_tables(self, table_do: CodegenTableDO) -> list[dict]:
        """加载主子表的子表信息"""
        from module_infra.definitions.enums.codegen.codegen_template_type_enum import (
            CodegenTemplateTypeEnum,
        )

        if table_do.template_type != CodegenTemplateTypeEnum.SUB.value:
            return []
        sub_table_list = await self.codegen_table_mapper.select_list_by_master_table_id(table_do.id)
        result = []
        for sub_table in sub_table_list:
            sub_columns = await self.codegen_column_mapper.select_list_by_table_id(sub_table.id)
            sub_join_column = None
            if sub_table.sub_join_column_id:
                sub_join_column = next(
                    (c for c in sub_columns if c.id == sub_table.sub_join_column_id), None
                )
            result.append(
                {
                    "table": sub_table,
                    "columns": sub_columns,
                    "sub_join_column": sub_join_column,
                    "sub_join_many": sub_table.sub_join_many,
                }
            )
        return result
