from __future__ import annotations

from typing import override

from pydantic import ValidationError

from framework.common.enums import StatusEnum
from framework.common.exception import ConfigurationException, ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    DatabaseErrorCodes,
    DatabaseException,
    DatabaseStarter,
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_i18n.public import I18nTranslator
from framework.starter_web.public import RequestContext
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_save_req_vo import (
    DataSourceConfigSaveReqVO,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO
from module_infra.dal.mapper.data_source.data_source_config_mapper import DataSourceConfigMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.data_source.data_source_config_service import DataSourceConfigService
from module_infra.util.data_source.data_source_utils import DataSourceUtils


@service(interface=DataSourceConfigService)
class DataSourceConfigServiceImpl(DataSourceConfigService):
    """数据源配置服务实现类"""

    data_source_config_mapper: DataSourceConfigMapper = Inject()
    database_starter: DatabaseStarter = Inject()
    data_source_utils: DataSourceUtils = Inject()
    translator: I18nTranslator = Inject()

    @override
    @transactional
    async def create_data_source_config(self, create_req_vo: DataSourceConfigSaveReqVO) -> int:
        """创建数据源配置"""
        await self._validate_data_source_config_name_unique(None, create_req_vo.name)
        if not create_req_vo.url:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_URL_REQUIRED)
        data_source_config = DataSourceConfigDO(
            **create_req_vo.to_write_dict(
                fields={
                    "id",
                    "name",
                    "url",
                    "status",
                    "db_type",
                    "source_type",
                    "is_default",
                    "pool_size",
                    "max_overflow",
                    "pool_recycle",
                    "pool_timeout",
                    "echo",
                    "remark",
                },
                exclude_unset=False,
            )
        )
        await self._require_connection(data_source_config)
        if create_req_vo.is_default:
            await self._update_default_data_source(create_req_vo.source_type)
        await self.data_source_config_mapper.insert(data_source_config)
        if data_source_config.status == StatusEnum.ENABLE.code:
            await self._reload_datasources()
        return data_source_config.id

    @override
    @transactional
    async def update_data_source_config(self, update_req_vo: DataSourceConfigSaveReqVO) -> None:
        """更新数据源配置"""
        original_config = await self._validate_data_source_config_exists(update_req_vo.id)
        await self._validate_data_source_config_name_unique(update_req_vo.id, update_req_vo.name)
        if update_req_vo.url is None:
            update_req_vo.url = original_config.url
        if update_req_vo.url != original_config.url:
            test_config = DataSourceConfigDO(
                **update_req_vo.to_write_dict(
                    fields={
                        "id",
                        "name",
                        "url",
                        "status",
                        "db_type",
                        "source_type",
                        "is_default",
                        "pool_size",
                        "max_overflow",
                        "pool_recycle",
                        "pool_timeout",
                        "echo",
                        "remark",
                    },
                    exclude_unset=False,
                )
            )
            await self._require_connection(test_config)
        if update_req_vo.is_default:
            await self._update_default_data_source(update_req_vo.source_type)
        update_do = DataSourceConfigDO(
            **update_req_vo.to_write_dict(
                fields={
                    "id",
                    "name",
                    "url",
                    "status",
                    "db_type",
                    "source_type",
                    "is_default",
                    "pool_size",
                    "max_overflow",
                    "pool_recycle",
                    "pool_timeout",
                    "echo",
                    "remark",
                },
                exclude_unset=False,
            )
        )
        await self.data_source_config_mapper.update_by_id(update_do)
        await self._reload_datasources()

    @override
    @transactional
    async def update_status(self, data_source_config_id: int, status: int) -> None:
        """更新数据源配置状态"""
        await self._validate_data_source_config_exists(data_source_config_id)
        update_obj = DataSourceConfigDO(id=data_source_config_id, status=status)
        await self.data_source_config_mapper.update_by_id(update_obj)
        await self._reload_datasources()

    @override
    @transactional
    async def delete_data_source_config(self, id: int) -> None:
        """删除数据源配置"""
        data_source_config = await self._validate_data_source_config_exists(id)
        if data_source_config.is_default:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_DELETE_DEFAULT)
        await self.data_source_config_mapper.delete_by_id(id)
        if data_source_config.status == StatusEnum.ENABLE.code:
            await self._reload_datasources()

    @override
    async def get_data_source_config(self, id: int) -> DataSourceConfigDO | None:
        """获取数据源配置"""
        return await self.data_source_config_mapper.select_by_id(id)

    @override
    async def get_data_source_config_page(
        self, page_req_vo: DataSourceConfigPageReqVO
    ) -> PageResult[DataSourceConfigDO]:
        """获取数据源配置分页"""
        return await self.data_source_config_mapper.select_page(page_req_vo)

    @override
    async def get_data_source_config_list(self) -> list[DataSourceConfigDO]:
        """获取所有数据源配置列表"""
        return await self.data_source_config_mapper.select_list()

    @override
    async def get_data_source_config_list_by_status(self, status: int) -> list[DataSourceConfigDO]:
        """根据状态获取数据源配置列表"""
        return await self.data_source_config_mapper.select_list_by_status(status)

    @override
    async def test_data_source_config(self, id: int) -> tuple[bool, str]:
        """测试数据源配置连接"""
        accept_language = RequestContext.current().accept_language
        try:
            data_source_config = await self._validate_data_source_config_exists(id)
            await self._require_connection(data_source_config)
        except ServiceException as error:
            return False, self.translator.translate_any_scope(
                error.message_key,
                accept_language,
                default=error.msg,
                args=error.format_args,
            )
        return True, self.translator.translate_any_scope(
            "infra.data_source.test_success", accept_language, default="连接成功"
        )

    async def _require_connection(self, config: DataSourceConfigDO) -> None:
        """仅将已知连接与配置失败转换为业务错误，保留原因且不公开凭证。"""
        try:
            await self.data_source_utils.test_connection(config)
        except (ConfigurationException, ValidationError, DatabaseException, OSError) as error:
            if isinstance(error, DatabaseException) and error.error_code not in (
                DatabaseErrorCodes.ERROR,
                DatabaseErrorCodes.CONNECTION_FAILED,
                DatabaseErrorCodes.POOL_TIMEOUT,
                DatabaseErrorCodes.STATEMENT_TIMEOUT,
            ):
                raise
            raise ServiceException(
                ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED, type(error).__name__
            ) from error

    @override
    async def get_default_data_source_config(self, source_type: int) -> DataSourceConfigDO | None:
        """获取默认数据源配置"""
        return await self.data_source_config_mapper.select_default_datasource(source_type)

    async def _validate_data_source_config_exists(self, id: int) -> DataSourceConfigDO:
        """校验数据源配置是否存在"""
        data_source_config = await self.data_source_config_mapper.select_by_id(id)
        if not data_source_config:
            raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_DATA_NOT_EXISTS)
        return data_source_config

    async def _validate_data_source_config_name_unique(self, id: int | None, name: str) -> None:
        """校验数据源名称是否唯一"""
        data_source_config = await self.data_source_config_mapper.select_by_name(name)
        if data_source_config is None:
            return
        if id is not None and data_source_config.id == id:
            return
        raise ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_NAME_DUPLICATE, name)

    async def _update_default_data_source(self, source_type: int) -> None:
        """将同类型的其他数据源设置为非默认"""
        default_data_source = await self.get_default_data_source_config(source_type)
        if default_data_source:
            default_data_source.is_default = False
            await self.data_source_config_mapper.update_by_id(default_data_source)

    async def _reload_datasources(self):
        if self.database.settings.dynamic_enabled:
            self.database.after_commit(
                self.database_starter.refresh_sources, name="infra-data-source-refresh"
            )

    database: SessionProvider = Inject()
