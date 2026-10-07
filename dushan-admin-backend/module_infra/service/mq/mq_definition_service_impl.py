from __future__ import annotations

from typing import override

from framework.common.exception import IllegalArgumentException, ServiceException
from framework.common.page import PageResult
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    MQService,
)
from module_infra.controller.admin.mq.vo.mq.mq_consumer_resp_vo import MqConsumerRespVO
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO
from module_infra.controller.admin.mq.vo.mq.mq_save_req_vo import MqSaveReqVO
from module_infra.dal.dataobject.mq.mq_do import MqDO
from module_infra.dal.mapper.mq.mq_definition_mapper import MqDefinitionMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.mq.mq_definition_service import MqDefinitionService


@service(interface=MqDefinitionService)
class MqDefinitionServiceImpl(MqDefinitionService):
    mq: MQService = Inject()
    mq_mapper: MqDefinitionMapper = Inject()

    async def get_registered_consumers(self) -> list[MqConsumerRespVO]:
        return [
            MqConsumerRespVO(
                key=definition.key, topic=definition.destination, retry_count=definition.retry.count
            )
            for definition in sorted(self.mq.declarations, key=lambda item: item.key)
        ]

    @override
    async def create_mq_definition(self, create_req_vo: MqSaveReqVO) -> int:
        await self._validate_before_save(None, create_req_vo.topic, create_req_vo.consumer)
        self._validate_declaration(create_req_vo)
        new_definition = MqDO(
            **create_req_vo.to_write_dict(
                fields={
                    "id",
                    "topic",
                    "consumer",
                    "retry_count",
                    "description",
                    "enabled",
                    "concurrency",
                    "prefetch",
                },
                exclude_unset=False,
            )
        )
        await self.mq_mapper.insert(new_definition)
        return new_definition.id

    @override
    async def update_mq_definition(self, update_req_vo: MqSaveReqVO) -> None:
        await self._validate_before_save(
            update_req_vo.id, update_req_vo.topic, update_req_vo.consumer
        )
        self._validate_declaration(update_req_vo)
        update_definition = MqDO(
            **update_req_vo.to_write_dict(
                fields={
                    "id",
                    "topic",
                    "consumer",
                    "retry_count",
                    "description",
                    "enabled",
                    "concurrency",
                    "prefetch",
                },
                exclude_unset=False,
            )
        )
        await self.mq_mapper.update_by_id(update_definition)

    @override
    async def delete_mq_definition(self, id: int) -> None:
        await self._validate_definition_exists(id)
        await self.mq_mapper.delete_by_id(id)

    @override
    async def get_mq_definition(self, id: int) -> MqDO | None:
        return await self.mq_mapper.select_by_id(id)

    @override
    async def get_mq_definition_page(self, page_req_vo: MqPageReqVO) -> PageResult[MqDO]:
        return await self.mq_mapper.select_page(page_req_vo)

    @override
    async def get_mq_definition_list(
        self, topic: str | None = None, consumer: str | None = None
    ) -> list[MqDO]:
        return await self.mq_mapper.select_filtered_list(topic=topic, consumer=consumer)

    async def _validate_definition_exists(self, id: int) -> MqDO:
        definition = await self.get_mq_definition(id)
        if not definition:
            raise ServiceException(ErrorCodeConstants.MQ_DEFINITION_NOT_EXISTS)
        return definition

    async def _validate_before_save(self, id: int | None, topic: str, consumer: str) -> None:
        definition_by_topic = await self.mq_mapper.select_by_topic(topic)
        if definition_by_topic and (id is None or definition_by_topic.id != id):
            raise ServiceException(ErrorCodeConstants.MQ_DEFINITION_TOPIC_EXISTS)
        definition_by_consumer = await self.mq_mapper.select_by_consumer(consumer)
        if definition_by_consumer and (id is None or definition_by_consumer.id != id):
            raise ServiceException(ErrorCodeConstants.MQ_DEFINITION_CONSUMER_EXISTS)

    def _validate_declaration(self, request):
        declarations = {definition.key: definition for definition in self.mq.declarations}
        if request.consumer not in declarations:
            raise IllegalArgumentException(msg="消费者未注册，请先部署消费者，再从已注册列表选择")
        definition = declarations[request.consumer]
        if request.topic != definition.destination or request.retry_count != definition.retry.count:
            raise IllegalArgumentException(msg="主题和重试次数必须与所选消费者声明一致")
