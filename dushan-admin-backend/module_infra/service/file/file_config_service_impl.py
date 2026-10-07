from uuid import uuid4

from sqlalchemy import select

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.dal.mapper.file.file_config_mapper import FileConfigMapper
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.framework.file.core.client.file_client_factory import FileClientFactory
from module_infra.framework.file.core.enums.file_storage_enum import FileStorageEnum
from module_infra.service.file.file_config_service import FileConfigService


@service(interface=FileConfigService)
class FileConfigServiceImpl(FileConfigService):
    mapper: FileConfigMapper = Inject()
    files: FileMapper = Inject()
    factory: FileClientFactory = Inject()
    database: SessionProvider = Inject()

    @staticmethod
    def _config(storage, values, previous=None):
        model = FileStorageEnum.from_code(storage).config_class
        aliases = {
            field.alias: name
            for name, field in model.model_fields.items()
            if field.alias is not None
        }
        values = {aliases.get(key, key): value for key, value in values.items()}
        if previous is not None:
            for key in ("password", "access_secret", "access_key"):
                if values.get(key) in (None, "", "******", "[REDACTED]") and key in previous:
                    values[key] = previous[key]
        return (
            FileStorageEnum.from_code(storage)
            .config_class.model_validate(values)
            .model_dump(mode="json", by_alias=False)
        )

    @transactional
    async def create_file_config(self, create_req_vo):
        row = FileConfigDO(
            **create_req_vo.to_write_dict(
                fields={"name", "storage", "remark"}, exclude_unset=False
            ),
            config=self._config(create_req_vo.storage, create_req_vo.config),
            master=False,
        )
        await self.mapper.insert(row)
        return row.id

    @transactional
    async def update_file_config(self, update_req_vo):
        old = await self._require(update_req_vo.id)
        values = update_req_vo.to_write_dict(
            fields={"id", "name", "storage", "remark"}, exclude_unset=False
        )
        if update_req_vo.storage != old.storage and await self.files.select_count_by_config_id(
            old.id
        ):
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_HAS_FILE)
        values["config"] = self._config(
            update_req_vo.storage,
            update_req_vo.config,
            old.config if update_req_vo.storage == old.storage else None,
        )
        await self.mapper.update_by_id(FileConfigDO(**values))
        self.database.after_commit(lambda: self.factory.evict(old.id), name="file-config-update")

    @transactional
    async def update_file_config_master(self, file_config_id):
        row = await self._require(file_config_id)
        if row.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS)
        async with self.database.transaction() as session:
            await session.execute(select(FileConfigDO.id).with_for_update())
            await self.mapper.update_by_condition({"master": False}, FileConfigDO.master.is_(True))
            await self.mapper.update_by_id(FileConfigDO(id=file_config_id, master=True))

    @transactional
    async def delete_file_config(self, file_config_id):
        row = await self._require(file_config_id)
        if row.master:
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_DELETE_FAIL_MASTER)
        if await self.files.select_count_by_config_id(file_config_id):
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_HAS_FILE)
        await self.mapper.delete_by_id(file_config_id)
        self.database.after_commit(
            lambda: self.factory.evict(file_config_id), name="file-config-delete"
        )

    @transactional
    async def delete_file_config_batch(self, ids):
        for identifier in ids:
            await self.delete_file_config(identifier)
        return len(ids)

    async def get_file_config(self, file_config_id):
        return await self.mapper.select_by_id(file_config_id)

    async def get_file_config_page(self, page_req_vo):
        return await self.mapper.select_page(page_req_vo)

    async def get_file_config_list(self):
        return await self.mapper.select_enabled_list()

    async def test_file_config(self, file_config_id):
        client = await self.get_file_client(file_config_id)
        if client is None:
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS)
        path = "connection-test/" + uuid4().hex + ".txt"
        content = b"dushan storage connection test"
        url = await client.upload(path, content, "text/plain")
        try:
            if await client.get_content(path) != content:
                raise OSError("文件存储读写内容不一致")
        finally:
            await client.delete(path)
        return url

    async def get_file_client(self, config_id):
        row = (
            await self.mapper.select_by_master()
            if config_id == 0
            else await self.mapper.select_by_id(config_id)
        )
        if row is None or row.status != StatusEnum.ENABLE.code:
            return None
        return await self.factory.get_or_create_client(row.id, row.storage, row.config)

    async def get_master_file_client(self):
        return await self.get_file_client(0)

    async def _require(self, identifier: int) -> FileConfigDO:
        row = await self.mapper.select_by_id(identifier)
        if row is None:
            raise ServiceException(ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS)
        return row
