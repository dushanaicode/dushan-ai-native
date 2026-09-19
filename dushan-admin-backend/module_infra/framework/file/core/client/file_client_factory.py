import asyncio

from framework.common.utils import CleanupUtils
from framework.starter_di.public import (
    Inject,
    framework,
    pre_destroy_hook,
)
from module_infra.dal.mapper.file.file_content_mapper import FileContentMapper
from module_infra.framework.file.core.client.db.db_file_client import DBFileClient
from module_infra.framework.file.core.enums.file_storage_enum import FileStorageEnum


@framework
class FileClientFactory:
    contents: FileContentMapper = Inject()

    def __init__(self):
        self.clients = {}
        self.lock = asyncio.Lock()

    async def get_or_create_client(self, config_id, storage, config_dict):
        kind = FileStorageEnum.from_code(storage)
        config = kind.config_class.model_validate(config_dict)
        async with self.lock:
            old = self.clients.get(config_id)
            if old is not None and type(old) is kind.client_class and old.config == config:
                return old
            client = (
                kind.client_class(config_id, config, self.contents)
                if kind.client_class is DBFileClient
                else kind.client_class(config_id, config)
            )
            try:
                await client.init()
            except BaseException:
                await client.close()
                raise
            self.clients[config_id] = client
            if old is not None:
                await old.close()
            return client

    async def evict(self, config_id):
        async with self.lock:
            client = self.clients.pop(config_id, None)
            if client is not None:
                await client.close()

    @pre_destroy_hook
    async def close_all_clients(self):
        errors = []
        for client in self.clients.values():
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                client.close, "文件客户端关闭"
            )
            if error is not None:
                errors.append(error)
            if cancellation is not None:
                errors.append(cancellation)
        self.clients.clear()
        if errors:
            raise BaseExceptionGroup("文件客户端关闭失败", errors)
